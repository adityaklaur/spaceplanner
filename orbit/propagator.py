"""Orbit propagation using SGP4."""
import numpy as np
from astropy.time import Time

from orbit.tle_loader import TLEOrbit


def propagate_orbit(
    orbit: TLEOrbit,
    duration_hours: float = 2,
    steps: int = 60,
    start_time=None,
):
    """Propagate a TLE orbit over a simulation window.

    Parameters
    ----------
    orbit : TLEOrbit
        Parsed SGP4 satellite.
    duration_hours : float
        Length of the future screening window.
    steps : int
        Number of samples in the window.
    start_time : astropy.time.Time or compatible, optional
        Common propagation start time. If omitted, current UTC is used.

    Returns
    -------
    times_seconds : ndarray
        Seconds from ``start_time``.
    positions_km : ndarray, shape (N, 3)
        TEME position vectors in kilometres.
    """
    if duration_hours <= 0:
        raise ValueError("duration_hours must be positive")
    if steps < 2:
        raise ValueError("steps must be at least 2")

    start = Time.now() if start_time is None else Time(start_time)
    times = np.linspace(0.0, float(duration_hours) * 3600.0, int(steps))
    base_jd = float(start.utc.jd)
    positions = []

    for seconds in times:
        jd_value = base_jd + seconds / 86400.0
        jd_whole = float(np.floor(jd_value))
        jd_fraction = float(jd_value - jd_whole)
        error_code, position, _velocity = orbit.satellite.sgp4(jd_whole, jd_fraction)
        if error_code != 0:
            raise RuntimeError(f"SGP4 propagation failed with error code {error_code}")
        positions.append(position)

    return times, np.asarray(positions, dtype=float)
