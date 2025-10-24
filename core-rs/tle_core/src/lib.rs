use pyo3::exceptions::{PyNotImplementedError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule, PyTuple};
use pyo3::Bound;

fn checksum_inner(line: &str) -> bool {
    let trimmed = line.trim_end();
    let mut chars = trimmed.chars();
    let last = match chars.next_back() {
        Some(ch) => ch,
        None => return false,
    };
    let expected = match last.to_digit(10) {
        Some(v) => v,
        None => return false,
    };
    let mut total = 0u32;
    for ch in chars {
        if ch.is_ascii_digit() {
            total += ch.to_digit(10).unwrap();
        } else if ch == '-' {
            total += 1;
        }
    }
    total % 10 == expected
}

fn catnum_field(line: &str) -> String {
    line.get(2..7).unwrap_or("").trim().to_string()
}

fn ensure_source(src: &str) -> String {
    if src.is_empty() {
        "unknown".to_string()
    } else {
        src.to_string()
    }
}

#[pyfunction(signature = (text, norad_id="", source=""))]
fn parse(text: &str, norad_id: &str, source: &str) -> PyResult<(String, Option<String>, String, String, String)> {
    let lines: Vec<String> = text
        .lines()
        .map(|l| l.trim())
        .filter(|l| !l.is_empty())
        .map(|l| l.to_string())
        .collect();

    let mut name: Option<String> = None;
    let mut line1: Option<String> = None;
    let mut line2: Option<String> = None;

    for idx in 0..lines.len() {
        if lines[idx].starts_with("1 ") && idx + 1 < lines.len() && lines[idx + 1].starts_with("2 ") {
            if idx > 0 && !lines[idx - 1].starts_with("1 ") && !lines[idx - 1].starts_with("2 ") {
                name = Some(lines[idx - 1].trim().to_string());
            }
            line1 = Some(lines[idx].clone());
            line2 = Some(lines[idx + 1].clone());
            break;
        }
    }

    if line1.is_none() || line2.is_none() {
        let data: serde_json::Value = serde_json::from_str(text)
            .map_err(|_| PyValueError::new_err("Could not locate TLE line pair in response"))?;
        if let Some(obj) = data.as_object() {
            match (obj.get("line1"), obj.get("line2")) {
                (Some(l1), Some(l2)) => {
                    line1 = Some(l1.as_str().unwrap_or_default().to_string());
                    line2 = Some(l2.as_str().unwrap_or_default().to_string());
                    if let Some(n) = obj.get("name") {
                        if !n.is_null() {
                            name = Some(n.as_str().unwrap_or_default().to_string());
                        }
                    }
                }
                _ => return Err(PyValueError::new_err("Could not locate TLE line pair in response")),
            }
        } else {
            return Err(PyValueError::new_err("Could not locate TLE line pair in response"));
        }
    }

    let line1 = line1.ok_or_else(|| PyValueError::new_err("Empty TLE line detected"))?;
    let line2 = line2.ok_or_else(|| PyValueError::new_err("Empty TLE line detected"))?;

    if !line1.starts_with("1 ") || !line2.starts_with("2 ") {
        return Err(PyValueError::new_err("Bad TLE line prefixes"));
    }
    if !checksum_inner(&line1) || !checksum_inner(&line2) {
        return Err(PyValueError::new_err("Checksum failed"));
    }

    let cat1 = catnum_field(&line1);
    let cat2 = catnum_field(&line2);
    if cat1 != cat2 {
        return Err(PyValueError::new_err("Catalog numbers differ between L1 and L2"));
    }

    if !norad_id.is_empty() && norad_id.chars().all(|c| c.is_ascii_digit()) {
        let cat_digits: String = cat1.chars().filter(|c| !c.is_whitespace()).collect();
        if cat_digits.chars().all(|c| c.is_ascii_digit()) {
            if let (Ok(req), Ok(actual)) = (norad_id.parse::<i64>(), cat_digits.parse::<i64>()) {
                if req != actual {
                    return Err(PyValueError::new_err("Catalog number does not match requested NORAD ID"));
                }
            }
        }
    }

    let resolved_id = if norad_id.is_empty() {
        cat1.trim().to_string()
    } else {
        norad_id.to_string()
    };

    Ok((
        resolved_id,
        name,
        line1,
        line2,
        ensure_source(source).to_string(),
    ))
}

#[pyfunction]
fn checksum(line: &str) -> PyResult<bool> {
    Ok(checksum_inner(line))
}

#[pyfunction]
fn epoch(py: Python<'_>, line1: &str) -> PyResult<PyObject> {
    if line1.len() < 32 {
        return Err(PyValueError::new_err("Line 1 too short to contain epoch"));
    }
    let year2: i32 = line1[18..20]
        .parse()
        .map_err(|_| PyValueError::new_err("Invalid epoch year"))?;
    let doy: f64 = line1[20..32]
        .trim()
        .parse()
        .map_err(|_| PyValueError::new_err("Invalid epoch day"))?;
    let year = if year2 >= 57 { 1900 + year2 } else { 2000 + year2 };
    let day_int = doy.floor();
    let frac = doy - day_int;
    let total_seconds = frac * 86400.0;
    if total_seconds < 0.0 {
        return Err(PyValueError::new_err("Epoch fraction produced negative seconds"));
    }
    let mut secs_part = total_seconds.floor();
    let mut micros = ((total_seconds - secs_part) * 1_000_000.0).round();
    if micros >= 1_000_000.0 {
        secs_part += 1.0;
        micros -= 1_000_000.0;
    }

    let datetime = py.import_bound("datetime")?;
    let datetime_cls = datetime.getattr("datetime")?;
    let timezone = datetime.getattr("timezone")?.getattr("utc")?;
    let kwargs = PyDict::new_bound(py);
    kwargs.set_item("tzinfo", &timezone)?;
    let base = datetime_cls.call((year, 1, 1, 0, 0, 0), Some(&kwargs))?;
    let delta_kwargs = PyDict::new_bound(py);
    delta_kwargs.set_item("days", (day_int as i64) - 1)?;
    delta_kwargs.set_item("seconds", secs_part as i64)?;
    delta_kwargs.set_item("microseconds", micros as i64)?;
    let delta = datetime.getattr("timedelta")?.call((), Some(&delta_kwargs))?;
    let result = base.call_method1("__add__", (&delta,))?;
    Ok(result.into_py(py))
}

#[pyfunction]
fn sgp4(_args: &Bound<'_, PyTuple>, _kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<()> {
    Err(PyNotImplementedError::new_err(
        "SGP4 propagation not implemented in Rust backend",
    ))
}

#[pymodule]
fn _tle_core(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse, m)?)?;
    m.add_function(wrap_pyfunction!(checksum, m)?)?;
    m.add_function(wrap_pyfunction!(epoch, m)?)?;
    m.add_function(wrap_pyfunction!(sgp4, m)?)?;
    // Keep module doc minimal but informative.
    m.add("__doc__", "Rust-accelerated primitives for tle_fetcher")?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{catnum_field, checksum_inner, parse};
    use pyo3::prelude::*;

    const SAMPLE: &str = "ISS (ZARYA)\n1 25544U 98067A   20344.91719907  .00001264  00000-0  29621-4 0  9993\n2 25544  51.6466 223.8666 0002416  90.3778  30.6140 15.48970462256430\n";

    #[test]
    fn checksum_matches_python() {
        assert!(checksum_inner("1 25544U 98067A   20344.91719907  .00001264  00000-0  29621-4 0  9993"));
    }

    #[test]
    fn parse_basic_payload() {
        Python::with_gil(|_py| {
            let result = parse(SAMPLE, "25544", "celestrak").expect("parse ok");
            assert_eq!(result.0, "25544");
            assert!(result.2.starts_with("1 "));
            assert!(result.3.starts_with("2 "));
            assert_eq!(catnum_field(&result.2), "25544");
        });
    }
}
