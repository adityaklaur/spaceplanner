import requests

def fetch_multiple_tles():
    try:
        url = "https://celestrak.org/NORAD/elements/stations.txt"
        response = requests.get(url, verify=False, timeout=5)

        if response.status_code == 200:
            lines = response.text.strip().split("\n")

            satellites = []

            for i in range(0, len(lines) - 2, 3):
                name = lines[i].strip()
                tle1 = lines[i+1].strip()
                tle2 = lines[i+2].strip()

                # ✅ VALIDATION
                if tle1.startswith("1 ") and tle2.startswith("2 "):
                    satellites.append((name, tle1, tle2))

            return satellites[:5]

    except Exception:
        pass

    print("⚠️ Using fallback")

    return [
        ("ISS",
         "1 25544U 98067A   24067.54791435  .00016717  00000+0  10270-3 0  9993",
         "2 25544  51.6436  21.4977 0007417  69.6797  42.8652 15.49815384435014")
    ]