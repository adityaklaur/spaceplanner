from poliastro.bodies import Earth
from poliastro.twobody import Orbit
from astropy import units as u
import numpy as np


def create_orbit(altitude_km):
    return Orbit.circular(Earth, alt=altitude_km * u.km, inc=45 * u.deg)


def propagate_orbit(orbit, duration_hours=2, steps=50):
    """
    Simulate orbit motion over time
    """
    times = np.linspace(0, duration_hours * 3600, steps) * u.s
    positions = []

    for t in times:
        new_orbit = orbit.propagate(t)
        r = new_orbit.r.to(u.km).value
        positions.append(r)

    return times.value, np.array(positions)