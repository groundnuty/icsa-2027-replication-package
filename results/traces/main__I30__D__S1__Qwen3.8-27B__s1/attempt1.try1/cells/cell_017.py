import numpy as np
z = np.load('/work/sst_region.npz', allow_pickle=False)
A = z['A']; dates = [str(d) for d in z['dates']]
d2i = {d: i for i, d in enumerate(dates)}
ext_n = d2i['2003-01-05'] + 1
ext = A[:ext_n]
mdays = [31,29,31,30,31,30,31,31,30,31,30,31]
cum = [0]
for m in mdays: cum.append(cum[-1]+m)
def doy(s): return cum[int(s[5:7])-1] + int(s[8:10])
doy_ext = np.array([doy(s) for s in dates[:ext_n]])
base_s, base_e = d2i['1992-01-01'], d2i['2002-12-31'] + 1
b_idx = np.arange(base_s, base_e); b_doy = doy_ext[b_idx]

def pool_mask(d):
    ib = b_idx[b_doy == d]
    starts = np.clip(ib-5, 0, ext_n-1); ends = np.clip(ib+5,0,ext_n-1)+1
    m = np.zeros(ext_n+1, np.int32); np.add.at(m, starts, 1); np.add.at(m, ends, -1)
    return np.cumsum(m)[:-1] > 0

thr = np.full((367, 60, 60), np.nan, dtype=np.float64)
cli = np.full((367, 60, 60), np.nan, dtype=np.float64)
for d in range(1, 367):
    if d == 60: continue
    idx = np.where(pool_mask(d))[0]
    pool = ext[idx]                                  # (n_d, 60, 60)
    f = np.isfinite(pool)                            # (n_d, 60, 60)
    c = f.sum(axis=0).astype(np.float64)             # (60,60)
    s = np.where(f, pool, 0.0).sum(axis=0)           # (60,60)
    cli[d] = np.where(c > 0, s / np.where(c > 0, c, 1), np.nan)
    pf = np.where(f, pool, np.nan)
    q = np.full((60,60), np.nan)
    for i in range(60):
        for j in range(60):
            col = pf[:, i, j]
            if np.isfinite(col).any():
                q[i, j] = np.quantile(col, 0.9, method='hazen')
    thr[d] = q
thr[60] = 0.5 * (thr[59] + thr[61])
cli[60] = 0.5 * (cli[59] + cli[61])
print("thr NaN (d1..366):", int(np.isnan(thr[1:]).sum()), "= 307*366 =", 307*366)
print("cli NaN (d1..366):", int(np.isnan(cli[1:]).sum()))

def smooth31(X):
    acc = np.zeros_like(X); cnt = np.zeros_like(X)
    for k in range(-15, 16):
        R = np.roll(X, k, axis=0)
        acc += np.where(np.isnan(R), 0.0, R)
        cnt += (~np.isnan(R))
    return np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan)

thr_s = smooth31(thr)
cli_s = smooth31(cli)
print("thr_s NaN:", int(np.isnan(thr_s[1:]).sum()), " cli_s NaN:", int(np.isnan(cli_s[1:]).sum()))
np.savez_compressed('/work/thr_cli.npz', thr=thr, cli=cli, thr_s=thr_s, cli_s=cli_s,
                    dates=np.array(dates))

# --- independent cross-check: explicit per-cell loop for a few cells ---
import random
tgt = A[d2i['2010-06-01']:d2i['2010-08-31']+1]
sea = np.all(np.isfinite(tgt), axis=0)
sea_cells = np.argwhere(sea)
rng = random.Random(42)
samples = rng.sample(list(sea_cells), 5) + [np.array([30,30])]
ok = True
for (i, j) in samples:
    for d in [1, 59, 60, 61, 153, 214, 365, 366]:
        if d == 60:
            # verify fill
            t60 = 0.5*(thr[59,i,j]+thr[61,i,j]); c60 = 0.5*(cli[59,i,j]+cli[61,i,j])
        else:
            idx = np.where(pool_mask(d))[0]
            col = ext[idx, i, j]
            col = col[np.isfinite(col)]
            t60 = np.quantile(col, 0.9, method='hazen')
            c60 = col.mean()
        if not (np.isclose(thr[d,i,j], t60) and np.isclose(cli[d,i,j], c60)):
            ok = False
            print("MISMATCH cell", (i,j), "d", d, thr[d,i,j], t60, cli[d,i,j], c60)
print("cross-check ok:", ok)
c = (30,30)
print("sample thr_s d153/183/214:", thr_s[[153,183,214], c[0], c[1]])
print("sample cli_s d153/183/214:", cli_s[[153,183,214], c[0], c[1]])
