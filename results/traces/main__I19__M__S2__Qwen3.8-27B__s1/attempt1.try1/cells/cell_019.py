import numpy as np

def hazen_manual(vals, q=0.9):
    x = np.sort(vals[~np.isnan(vals)])
    n = len(x)
    if n == 0: return np.nan
    h1 = n*q + 0.5          # 1-based
    h1 = min(max(h1, 1.0), float(n))
    lo = int(np.floor(h1)); frac = h1 - lo
    if lo >= n: return x[-1]
    return x[lo-1] + frac*(x[lo]-x[lo-1])

tests = [
    [1,2,6,8],
    [1,2,np.nan,np.nan,6,8],
    [1,np.nan,2,4,6,8],
    [1,2,3,4,5,6,7,8,9],
    [np.nan]*6,
    [5,5,5,np.nan,5],
]
for t in tests:
    t = np.array(t, dtype=float)
    try:
        v = np.nanquantile(t, 0.9, method='hazen')
    except Exception as e:
        v = f"ERR {e}"
    print(f"data={np.round(np.asarray(t),2).tolist()}  nanquantile={v}  manual={hazen_manual(t)}")
