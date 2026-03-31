
import requests
import time

def fetch_multiple_tles():
    url = "https://celestrak.org/NORAD/elements/active.txt"

    for attempt in range(3):  # 🔁 retry 3 times
        try:
            response = requests.get(
                url,
                timeout=5,        # faster timeout
                verify=False      # skip SSL delay
            )

            if response.status_code == 200:
                lines = response.text.strip().split("\n")

                satellites = []
                for i in range(0, min(len(lines), 30), 3):  # limit satellites
                    name = lines[i].strip()
                    tle1 = lines[i+1].strip()
                    tle2 = lines[i+2].strip()
                    satellites.append((name, tle1, tle2))

                print("✅ Live TLE data loaded")
                return satellites[:5]  # limit for performance

        except Exception as e:
            print(f"⚠️ Attempt {attempt+1} failed... retrying")
            time.sleep(1)

    # 🔴 FALLBACK
    print("💾 Using offline data")

    return [
        ("ISS (ZARYA)",
         "1 25544U 98067A   24067.54791435  .00016717  00000+0  10270-3 0  9993",
         "2 25544  51.6436  21.4977 0007417  69.6797  42.8652 15.49815384435014"),

        ("HUBBLE SPACE TELESCOPE",
         "1 20580U 90037B   24067.53208918  .00000800  00000+0  38973-4 0  9991",
         "2 20580  28.4694  87.1294 0002951  87.5643 272.5655 15.09204592391234"),

        ("NOAA 15",
         "1 25338U 98030A   24067.51782528  .00000091  00000+0  74605-4 0  9998",
         "2 25338  98.7314  70.5982 0011643  90.5983 269.6413 14.25901522234567"),

        ("TERRA",
         "1 25994U 99068A   24067.50972847  .00000092  00000+0  65592-4 0  9996",
         "2 25994  98.2051  65.2113 0001154  88.4532 271.6783 14.57109876543210"),

        ("AQUA",
         "1 27424U 02022A   24067.50000000  .00000089  00000+0  61234-4 0  9992",
         "2 27424  98.1977  64.5123 0001200  85.1234 274.5678 14.57110000000000"),
    ]