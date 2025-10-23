# TLE Fetcher Utility  

This repository contains a simple terminal based utility for fetching up‭to‭date Two‑Line Element (TLE) data for satellites from the public [TLE API](https://tle.ivanstanojevic.me). Given a NORAD catalog ID, the script retrieves and displays the satellite's name and TLE lines, and optionally saves them to a `.tle` file.  

## Requirements  

- Python 3.x (tested with 3.8+).  
- Internet access to reach the TLE API (no API key required).  

## How to Use  

1. Clone the repository and navigate into it:  
   ```  
   git clone https://github.com/cywf/tle-fetcher.git  
   cd tle-fetcher  
   ```  
2. Run the script:  
   ```  
   python3 tle_fetcher.py  
   ```  
3. When prompted, enter a valid NORAD catalog ID (e.g., `25544` for the International Space Station). The script will call the TLE API endpoint `/satellite/{norad_cat_id}` and display:  
   - Satellite name.  
   - Line 1 of the TLE.  
   - Line 2 of the TLE.  
4. If you choose to save the TLE, it will be written to a file named `<NORAD_ID>.tle` in the current directory.  

## Example  

```  
Enter a NORAD catalog ID (or 'q' to quit): 25544  

Name: International Space Station (ZARYA)  
Line1: 1 25544U 98067A 23001.74462497 .00001435 00000-0 34779-4 0 9992  
Line2: 2 25544 51.6464 24.2704 0004064 69.5467 290.6355 15.48835264296862  
Would you like to save the TLE to a file? (y/n): y  
TLE saved to 25544.tle  
```  

Feel free to modify and extend this utility to search for satellites by name or integrate it into larger satellite-tracking workflows.
