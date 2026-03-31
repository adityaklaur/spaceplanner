from orbit.tle_fetcher import fetch_iss_tle

tle1, tle2 = fetch_iss_tle()

print("Live ISS TLE:")
print(tle1)
print(tle2)