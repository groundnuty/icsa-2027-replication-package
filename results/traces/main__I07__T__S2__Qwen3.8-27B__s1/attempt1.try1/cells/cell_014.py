
import numpy as np, pandas as pd, inspect
print("Series.quantile sig:", inspect.signature(pd.Series.quantile))
a = np.arange(1, 21, dtype=float)
b = a.copy(); b[3] = np.nan; b[17] = np.nan
def hf5(x, p):
    x = np.sort(x); n = len(x)
    h = (np.arange(1, n+1) - 0.5) / n
    return float(np.interp(p, h, x))
print("pd nan hazen 0.9:", pd.Series(b).quantile(0.9, interpolation='hazen'), "manual:", hf5(b[~np.isnan(b)], 0.9))
print("pd nan hazen 0.5:", pd.Series(b).quantile(0.5, interpolation='hazen'), "manual:", hf5(b[~np.isnan(b)], 0.5))
# all-NaN column behavior
s = pd.Series(np.full(121, np.nan))
print("all-NAN pd hazen:", s.quantile(0.9, interpolation='hazen'))
# DataFrame axis=0 path
df = pd.DataFrame(np.column_stack([b, a, np.full(121, np.nan)]))
print("df quantile:", df.quantile(0.9, interpolation='hazen', axis=0).tolist())
