
import numpy as np, pandas as pd, inspect
print(inspect.signature(np.quantile))
a = np.arange(1, 21, dtype=float)
for p in [0.9, 0.5, 0.1]:
    print(p, "np hazen:", np.quantile(a, p, method='hazen'), "pd hazen:", pd.Series(a).quantile(p, interpolation='hazen'))
# with NaN
b = np.arange(1, 21, dtype=float); b[3] = np.nan; b[17] = np.nan
for p in [0.9, 0.5]:
    print("nan", p, "pd hazen:", pd.Series(b).quantile(p, interpolation='hazen', skipna=True))
# manual type-5 for the NaN case: n=18 valid
import math
def hf5(x, p):
    x = np.sort(x)
    n = len(x)
    h = (np.arange(1, n+1) - 0.5) / n
    return float(np.interp(p, h, x))
print("manual hf5 nan 0.9:", hf5(b[~np.isnan(b)], 0.9), "0.5:", hf5(b[~np.isnan(b)], 0.5))
