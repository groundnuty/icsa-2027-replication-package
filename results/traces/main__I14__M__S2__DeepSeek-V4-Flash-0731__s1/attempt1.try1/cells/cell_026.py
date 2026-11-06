
import numpy as np
import pandas as pd
import pickle

times_int = np.load('/tmp/times.npy')
times = pd.to_datetime(times_int, unit='D')

with open('/tmp/pools.pkl', 'rb') as f:
    pools = pickle.load(f)

# Check pool for doy 366 (Dec 31)
pool_366 = pools[366]
print("Pool size for doy 366:", len(pool_366))
dates_366 = [times[i].date() for i in pool_366]
print("First 5:", dates_366[:5])
print("Last 5:", dates_366[-5:])

# Check pool for doy 1
pool_1 = pools[1]
print("\nPool size for doy 1:", len(pool_1))
dates_1 = [times[i].date() for i in pool_1]
print("First 5:", dates_1[:5])
print("Last 5:", dates_1[-5:])

# Check pool for doy 59 (Feb 28)
pool_59 = pools[59]
print("\nPool size for doy 59:", len(pool_59))
dates_59 = [times[i].date() for i in pool_59]
print("First 5:", dates_59[:5])
print("Last 5:", dates_59[-5:])

# Check pool for doy 61 (Mar 1)
pool_61 = pools[61]
print("\nPool size for doy 61:", len(pool_61))
dates_61 = [times[i].date() for i in pool_61]
print("First 5:", dates_61[:5])
print("Last 5:", dates_61[-5:])
