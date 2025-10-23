#!/usr/bin/env python3
import json
import urllib.request

def fetch_tle(norad_id):
    url = f"https://tle.ivanstanojevic.me/satellite/{norad_id}"
    try:
        with urllib.request.urlopen(url) as response:
            if response.status != 200:
                print(f"Error retrieving TLE: HTTP status {response.status}")
                return
            data = json.load(response)
    except Exception as e:
        print("Error retrieving TLE:", e)
        return
    print(f"\nName: {data.get('name')}")
    print("Line1:", data.get('line1'))
    print("Line2:", data.get('line2'))
    save = input("Would you like to save the TLE to a file? (y/n): ").strip().lower()
    if save == 'y':
        filename = f"{norad_id}.tle"
        with open(filename, 'w') as f:
            f.write(data.get('line1') + '\n' + data.get('line2') + '\n')
        print(f"TLE saved to {filename}")

def main():
    print("TLE Fetcher Utility")
    while True:
        user_input = input("Enter a NORAD catalog ID (or 'q' to quit): ").strip()
        if user_input.lower() in ('q', 'quit', 'exit'):
            break
        if not user_input.isdigit():
            print("Please enter a numeric NORAD catalog ID.")
            continue
        fetch_tle(user_input)

if __name__ == "__main__":
    main()
