/**
 * Satellite metadata fetching from SatNOGS and CelesTrak SATCAT
 */

export interface SatelliteMetadata {
  catid: number;
  name?: string;
  operator?: string;
  country?: string;
  mission?: string;
  aliases?: string[];
  orbit?: {
    type?: string;      // LEO, MEO, GEO
    period?: number;    // minutes
    inclination?: number; // degrees
  };
  status?: string;
  sources: string[];    // Track which APIs provided data
}

/**
 * Fetch metadata from SatNOGS DB API
 */
async function fetchSatNOGSMetadata(catid: number): Promise<Partial<SatelliteMetadata> | null> {
  try {
    const url = `https://db.satnogs.org/api/satellites/?norad_cat_id=${catid}`;
    const response = await fetch(url);
    
    if (!response.ok) {
      return null;
    }
    
    const data = await response.json();
    
    if (!Array.isArray(data) || data.length === 0) {
      return null;
    }
    
    const sat = data[0];
    
    return {
      catid,
      name: sat.name || undefined,
      status: sat.status || undefined,
      sources: ['SatNOGS'],
    };
  } catch (error) {
    console.warn(`Failed to fetch SatNOGS metadata for ${catid}:`, error);
    return null;
  }
}

/**
 * Fetch metadata from CelesTrak SATCAT
 */
async function fetchSATCATMetadata(catid: number): Promise<Partial<SatelliteMetadata> | null> {
  try {
    const url = `https://celestrak.org/satcat/records.php?CATNR=${catid}&FORMAT=JSON`;
    const response = await fetch(url);
    
    if (!response.ok) {
      return null;
    }
    
    const data = await response.json();
    
    if (!Array.isArray(data) || data.length === 0) {
      return null;
    }
    
    const sat = data[0];
    
    // Determine orbit type from period
    let orbitType: string | undefined;
    if (sat.PERIOD) {
      const period = parseFloat(sat.PERIOD);
      if (period < 128) {
        orbitType = 'LEO';
      } else if (period < 600) {
        orbitType = 'MEO';
      } else if (period >= 1400) {
        orbitType = 'GEO';
      }
    }
    
    return {
      catid,
      name: sat.OBJECT_NAME || sat.SATNAME || undefined,
      operator: sat.OWNER || undefined,
      country: sat.COUNTRY || undefined,
      orbit: {
        type: orbitType,
        period: sat.PERIOD ? parseFloat(sat.PERIOD) : undefined,
        inclination: sat.INCLINATION ? parseFloat(sat.INCLINATION) : undefined,
      },
      sources: ['SATCAT'],
    };
  } catch (error) {
    console.warn(`Failed to fetch SATCAT metadata for ${catid}:`, error);
    return null;
  }
}

/**
 * Merge metadata from multiple sources
 */
function mergeMetadata(
  satnogs: Partial<SatelliteMetadata> | null,
  satcat: Partial<SatelliteMetadata> | null
): SatelliteMetadata {
  const merged: SatelliteMetadata = {
    catid: satnogs?.catid || satcat?.catid || 0,
    sources: [],
  };
  
  if (satnogs) {
    merged.name = satnogs.name || merged.name;
    merged.status = satnogs.status || merged.status;
    merged.sources.push(...(satnogs.sources || []));
  }
  
  if (satcat) {
    merged.name = merged.name || satcat.name;
    merged.operator = satcat.operator || merged.operator;
    merged.country = satcat.country || merged.country;
    merged.orbit = satcat.orbit || merged.orbit;
    merged.sources.push(...(satcat.sources || []));
  }
  
  return merged;
}

/**
 * Fetch complete metadata for a satellite
 */
export async function fetchMetadata(catid: number): Promise<SatelliteMetadata> {
  const [satnogs, satcat] = await Promise.all([
    fetchSatNOGSMetadata(catid),
    fetchSATCATMetadata(catid),
  ]);
  
  return mergeMetadata(satnogs, satcat);
}

/**
 * Fetch metadata for multiple satellites
 */
export async function fetchMetadataBatch(catids: number[]): Promise<Map<number, SatelliteMetadata>> {
  const promises = catids.map(catid => fetchMetadata(catid));
  const results = await Promise.all(promises);
  
  const metadataMap = new Map<number, SatelliteMetadata>();
  results.forEach((metadata) => {
    metadataMap.set(metadata.catid, metadata);
  });
  
  return metadataMap;
}
