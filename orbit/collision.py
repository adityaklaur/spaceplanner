import numpy as np

def detect_collisions(sat_positions, threshold_km=50):
    """
    sat_positions: dict {name: positions_array}
    """
    alerts = []

    names = list(sat_positions.keys())

    for i in range(len(names)):
        for j in range(i + 1, len(names)):

            sat1 = names[i]
            sat2 = names[j]

            pos1 = sat_positions[sat1]
            pos2 = sat_positions[sat2]

            # Compare same time steps
            min_len = min(len(pos1), len(pos2))

            for k in range(min_len):
                d = np.linalg.norm(pos1[k] - pos2[k])

                if d < threshold_km:
                    alerts.append((sat1, sat2, d))
                    break

    return alerts