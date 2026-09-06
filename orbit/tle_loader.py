"""TLE loading utilities backed directly by SGP4.

Poliastro is intentionally not used here.  SGP4 is the standard propagation
model for TLEs, and using it directly keeps the runtime small and avoids the
Python-version constraints of the archived poliastro package.
"""
from dataclasses import dataclass

from astropy.time import Time
from sgp4.api import Satrec


@dataclass(frozen=True)
class TLEOrbit:
    """Small wrapper around an SGP4 satellite and its TLE epoch."""

    satellite: Satrec
    epoch: Time


def load_tle(tle_line1: str, tle_line2: str) -> TLEOrbit:
    """Parse two TLE lines and return an SGP4 orbit wrapper."""
    if not tle_line1.startswith("1 ") or not tle_line2.startswith("2 "):
        raise ValueError("Invalid TLE: expected line 1 and line 2 records")

    satellite = Satrec.twoline2rv(tle_line1.strip(), tle_line2.strip())
    epoch_jd = satellite.jdsatepoch + satellite.jdsatepochF
    epoch = Time(epoch_jd, format="jd", scale="utc")
    return TLEOrbit(satellite=satellite, epoch=epoch)
