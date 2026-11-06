import numpy as np, pickle, warnings
with open('/tmp/stepA2.pkl','rb') as fh: A = pickle.load(fh)
mem = A['mem']; arr_sea = A['arr_sea']; thresh_s = A['thresh_s']

d = 183; cell = 10
idxs = [((d + k - 1) % 366) for k in range(-15, 16)]   # doy values 168..198
print("window doys:", idxs[0], "..", idxs[-1], "n:", len(idxs))

def matlab_q(x, p=0.9):
    x = np.sort(x[np.isfinite(x)])
    n = len(x)
    if n == 0: return np.nan
    pp = (np.arange(1, n+1) - 0.5) / n
    return float(np.interp(p, pp, x))

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    q1, q2, qm = [], [], []
    for dd in idxs:
        pool = arr_sea[mem[:, dd-1]]
        q1.append(np.nanquantile(pool[:, cell], 0.9, method='hazen'))
        q2.append(np.nanquantile(pool, 0.9, axis=0, method='hazen')[cell])
        qm.append(matlab_q(pool[:, cell]))
q1, q2, qm = map(np.array, (q1, q2, qm))
print("mean 1-D:", q1.mean(), "\nmean 2-D:", q2.mean(), "\nmean matlab:", qm.mean(),
      "\nsaved smoothed:", thresh_s[d-1, cell])
print("max |q1-q2|:", np.abs(q1-q2).max(), " max |q1-qm|:", np.abs(q1-qm).max())
diff_doy = [idxs[j] for j in range(len(idxs)) if abs(q1[j]-q2[j]) > 1e-9]
print("doys where 1-D != 2-D:", diff_doy)
# sizes of those pools
for dd in diff_doy[:5]:
    p = arr_sea[mem[:, dd-1]][:, cell]
    print(f"  doy {dd}: n={len(p)} nan={int((~np.isfinite(p)).sum())} q1={np.nanquantile(p,0.9,method='hazen'):.6f}")
