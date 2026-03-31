from poliastro.bodies import Earth
from poliastro.twobody import Orbit
from astropy import units as u
from sgp4.api import Satrec, jday
from datetime import datetime
from astropy.time import Time


def load_tle(tle_line1, tle_line2):
    """
    Convert TLE → Poliastro Orbit object
    """

    # Create satellite from TLE
    satellite = Satrec.twoline2rv(tle_line1, tle_line2)

    # Current UTC time
    now = datetime.utcnow()

    # Convert to Julian date
    jd, fr = jday(
        now.year,
        now.month,
        now.day,
        now.hour,
        now.minute,
        now.second
    )

    # Propagate using SGP4
    error_code, position, velocity = satellite.sgp4(jd, fr)

    if error_code != 0:
        raise Exception(f"SGP4 error code: {error_code}")

    # Convert position & velocity to astropy units
    import numpy as np

    r = np.array(position) * u.km
    v = np.array(velocity) * u.km / u.s

    # Create orbit (IMPORTANT FIX HERE)
    orbit = Orbit.from_vectors(
        Earth,
        r,
        v,
        epoch=Time(now)
    )

    return orbit