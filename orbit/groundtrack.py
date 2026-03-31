import numpy as np
from astropy import units as u
from astropy.coordinates import GCRS, ITRS, CartesianRepresentation


def eci_to_latlon(positions_km, times, epoch):
    """
    Convert ECI coordinates to latitude & longitude
    """

    lats = []
    lons = []

    for i, pos in enumerate(positions_km):
        t = epoch + times[i] * u.s

        # Create space coordinate
        gcrs = GCRS(
            CartesianRepresentation(pos[0] * u.km,
                                    pos[1] * u.km,
                                    pos[2] * u.km),
            obstime=t
        )

        # Convert to Earth-fixed frame
        itrs = gcrs.transform_to(ITRS(obstime=t))

        # Get lat/lon
        location = itrs.earth_location
        lats.append(location.lat.deg)
        lons.append(location.lon.deg)

    return np.array(lats), np.array(lons)