
import numpy as np

x = np.array([1.0, np.nan, 2.0, 3.0, 4.0, 5.0, np.nan])
valid = x[~np.isnan(x)]

r1 = np.nanpercentile(x, 90, method='hazen')
r2 = np.percentile(valid, 90, method='hazen')
print(f"nanpercentile: {r1}, percentile on valid: {r2}, equal: {r1 == r2}")

# Also check the mean
m1 = np.nanmean(x)
m2 = np.mean(valid)
print(f"nanmean: {m1}, mean of valid: {m2}, equal: {m1 == m2}")
