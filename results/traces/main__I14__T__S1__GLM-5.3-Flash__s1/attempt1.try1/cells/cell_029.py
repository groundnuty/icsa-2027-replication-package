import numpy as np, pickle, warnings
with open('/tmp/stepA2.pkl','rb') as fh: A = pickle.load(fh)
mem = A['mem']; arr_sea = A['arr_sea']; thresh_s = A['thresh_s']

d = 183; cell = 10
idxs = [((d + k - 1) % 366) for k in range(-15, 16)]
vals = []
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for i in idxs:
        pool = arr_sea[mem[:, i-1]][:, cell]
        vals.append(np.nanquantile(pool, 0.9, method='hazen'))
manual = float(np.mean(vals))
saved = float(thresh_s[d-1, cell])
print("manual:", manual, "saved:", saved, "diff:", saved-manual)
print("vals min/max:", min(vals), max(vals))
# recompute raw thresh fully and compare smoothed
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    raw = np.full((366, arr_sea.shape[1]), np.nan)
    for i in range(1, 367):
        if i == 60: continue
        raw[i-1] = np.nanquantile(arr_sea[mem[:, i-1]], 0.9, axis=0, method='hazen')
raw[59] = 0.5*(raw[58] + raw[60])
ext = np.concatenate([raw[-15:], raw, raw[:15]], axis=0)
cs = np.vstack([np.zeros((1, raw.shape[1])), np.cumsum(ext, axis=0)])
re_s = (cs[31:] - cs[:-31]) / 31.0
print("max |recomputed_smooth - saved|:", np.abs(re_s - thresh_s).max())
print("saved doy183 cell10 raw (from check idxs mean):", manual)
print("raw[182,10]:", raw[182, 10], "mean raw window:", raw[idxs, 10].mean())
