from datetime import datetime, timedelta
import pickle

with open('/tmp/doy_pool_dates.pkl', 'rb') as f:
    doy_to_pool_dates = pickle.load(f)

# Check if Feb 29, 1992 is in the pools for DOY 59 and 61
feb29_1992 = datetime(1992, 2, 29)
feb29_1996 = datetime(1996, 2, 29)
feb29_2000 = datetime(2000, 2, 29)

for doy in [59, 60, 61]:
    pool = doy_to_pool_dates.get(doy, [])
    in_pool_1992 = feb29_1992 in pool
    in_pool_1996 = feb29_1996 in pool
    in_pool_2000 = feb29_2000 in pool
    print(f"DOY {doy}: pool size={len(pool)}, Feb29/1992 in pool={in_pool_1992}, Feb29/1996 in pool={in_pool_1996}, Feb29/2000 in pool={in_pool_2000}")

# Also verify DOY 60 has no pool
print(f"DOY 60 pool: {len(doy_to_pool_dates.get(60, []))}")
