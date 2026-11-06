import numpy as np, pickle, warnings
with open('/tmp/stepA2.pkl','rb') as fh: A = pickle.load(fh)
mem = A['mem']; arr_sea = A['arr_sea']

# MATLAB-equivalent: Q(p) = interp on plotting positions (i-0.5)/n
def matlab_q(x, p=0.9):
    x = np.sort(x[np.isfinite(x)])
    n = len(x)
    if n == 0: return np.nan
    pp = (np.arange(1, n+1) - 0.5) / n
    return float(np.interp(p, pp, x))

rng = np.random.default_rng(1)
worst = 0.0
for n in [7, 10, 50, 121, 131, 365]:
    x = rng.normal(10, 3, n)
    worst = max(worst, abs(matlab_q(x) - np.quantile(x, 0.9, method='hazen')))
# with NaNs (nanquantile ignores them -> same as filtering)
y = rng.normal(5, 2, 121).copy(); y[[3, 50, 100]] = np.nan
worst = max(worst, abs(matlab_q(y) - np.nanquantile(y, 0.9, method='hazen')))
print("max |MATLAB-style interp - numpy hazen| over tests:", worst)

# redo the doy-183 window check with the correct formula
d = 183; cell = 10
idxs = [((d + k - 1) % 366) for k in range(-15, 16)]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    vals = [matlab_q(arr_sea[mem[:, i-1]][:, cell]) for i in idxs]
print("window mean of MATLAB thresholds:", np.mean(vals), "| saved smoothed:", A['thresh_s'][d-1, cell],
      "| match:", np.isclose(np.mean(vals), A['thresh_s'][d-1, cell]))
vals_c = [np.nanmean(arr_sea[mem[:, i-1]][:, cell]) for i in idxs]
print("clim window match:", np.isclose(np.mean(vals_c), A['clim_s'][d-1, cell]))

# verify a sample of saved raw thresholds across doys/cells vs MATLAB formula
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import random
    random.seed(7)
    raw = np.full((366, 3300), np.nan)
    for i in range(1, 367):
        if i == 60: continue
        raw[i-1] = np.nanquantile(arr_sea[mem[:, i-1]], 0.9, axis=0, method='hazen')
bad = 0
for _ in range(40):
    i = random.choice([x for x in range(1, 367) if x != 60]); c = random.randrange(3300)
    if not np.isclose(raw[i-1, c], matlab_q(arr_sea[mem[:, i-1]][:, c])): bad += 1
print("raw threshold spot-checks failing:", bad, "/ 40")
print("sanity: numpy hazen n=10 p=0.9:", np.quantile(np.arange(1,11,dtype=float), 0.9, method='hazen'),
      "MATLAB-style:", matlab_q(np.arange(1,11,dtype=float)))
