
import numpy as np
import pandas as pd
import pickle

# Load
sst_data = np.load('/tmp/sst_data.npy')
times_int = np.load('/tmp/times.npy')
times = pd.to_datetime(times_int, unit='D')

with open('/tmp/pools.pkl', 'rb') as f:
    pools = pickle.load(f)

def compute_doy(month, day):
    if month == 1:
        return day
    elif month == 2:
        return 31 + day
    else:
        days_before = 60
        days_in_month = {3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}
        for m in range(3, month):
            days_before += days_in_month[m]
        return days_before + day

# Check pool for doy 153 (June 1)
pool_153 = pools[153]
print("Pool size for doy 153:", len(pool_153))
print("Pool dates:", [times[i].date() for i in pool_153])

# Verify: these should be dates within ±5 days of June 1 in years 1992-2002
# i.e., May 27 - June 6 of 1992-2002, plus extended range for edge years
# Check some dates
for i in pool_153[:10]:
    print(times[i].date())
