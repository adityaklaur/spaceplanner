"""Coordinate conversion helpers for ground-track display."""
import numpy as np
from astropy import units as u
from astropy.coordinates import CartesianRepresentation, ITRS, TEME
from astropy.time import Time
from astropy.utils import iers

# Railway/CI should not block while Astropy tries to download fresh IERS data.
iers.conf.auto_download = False


def eci_to_latlon(positions_km, times, epoch):
    """Convert SGP4 TEME positions to geodetic latitude/longitude.

    Parameters
    ----------
    positions_km : array-like, shape (N, 3)
        TEME coordinates in kilometres.
    times : array-like
        Seconds from ``epoch``.
    epoch : astropy.time.Time
        TLE epoch.
    """
    positions = np.asarray(positions_km, dtype=float)
    seconds = np.asarray(times, dtype=float)
    if positions.ndim != 2 or positions.shape[1] != 3:
        raise ValueError("positions_km must have shape (N, 3)")
    if len(positions) != len(seconds):
        raise ValueError("positions and times must have equal length")

    obstimes = Time(epoch) + seconds * u.s
    cart = CartesianRepresentation(
        x=positions[:, 0] * u.km,
        y=positions[:, 1] * u.km,
        z=positions[:, 2] * u.km,
    )
    teme = TEME(cart, obstime=obstimes)
    itrs = teme.transform_to(ITRS(obstime=obstimes))
    geodetic = itrs.earth_location.geodetic
    return np.asarray(geodetic.lat.deg), np.asarray(geodetic.lon.deg)
