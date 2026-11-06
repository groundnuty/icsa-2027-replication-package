
import pandas as pd
import numpy as np

ext_dates = pd.date_range('1991-12-27', '2003-01-05', freq='D')
base_dates = pd.date_range('1992-01-01', '2002-12-31', freq='D')

def fixed_doy(ts):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[ts.month - 1] + ts.day

base_doy = np.array([fixed_doy(d) for d in base_dates])

# Check pool sizes for all days, especially around 58-62
for d in range(55, 65):
    if d == 60:
        print(f"Day {d}: SKIPPED (no pool)")
        continue
    b_mask = (base_doy == d)
    b_dates_for_d = base_dates[b_mask]
    print(f"Day {d}: {len(b_dates_for_d)} baseline dates")
    pool_dates = set()
    for b in b_dates_for_d:
        for t in ext_dates:
            if abs((t - b).days) <= 5:
                pool_dates.add(t)
    print(f"  Pool has {len(pool_dates)} dates")
    if len(b_dates_for_d) < 11:
        print(f"  Baseline dates: {b_dates_for_d}")
