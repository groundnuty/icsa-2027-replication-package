import numpy as np
from datetime import date

z = np.load('/work/sst_region.npz', allow_pickle=False)
A = z['A']
dates = [str(d) for d in z['dates']]
d2i = {d: i for i, d in enumerate(dates)}
ext_n = d2i['2003-01-05'] + 1
tgt_s = d2i['2010-06-01']; tgt_e = d2i['2010-08-31'] + 1
base_s = d2i['1992-01-01']; base_e = d2i['2002-12-31'] + 1
ext = A[:ext_n]
ext_dates = dates[:ext_n]

mdays = [31,29,31,30,31,30,31,31,30,31,30,31]
cum = [0]
for m in mdays: cum.append(cum[-1]+m)
def doy(s):
    return cum[int(s[5:7])-1] + int(s[8:10])

doy_ext = np.array([doy(s) for s in ext_dates], dtype=np.int64)
doy_all = np.array([doy(s) for s in dates], dtype=np.int64)
b_idx = np.arange(base_s, base_e)
b_doy = doy_ext[b_idx]

masks = np.zeros((367, ext_n), dtype=bool)
for d in range(1, 367):
    if d == 60: continue
    ib = b_idx[b_doy == d]
    starts = np.clip(ib - 5, 0, ext_n-1)
    ends   = np.clip(ib + 5, 0, ext_n-1) + 1
    m = np.zeros(ext_n + 1, dtype=np.int32)
    np.add.at(m, starts, 1)
    np.add.at(m, ends, -1)
    masks[d] = np.cumsum(m)[:-1] > 0
pool_sizes = masks.sum(axis=1)
print("pool sizes: d1,d153,d244,d365,d366 =", pool_sizes[[1,153,244,365,366]])
print("pool size min/max (d!=60):", pool_sizes[1:][pool_sizes[1:]>0].min(), pool_sizes[1:].max())

thr = np.full((367, 60, 60), np.nan, dtype=np.float64)
cli = np.full((367, 60, 60), np.nan, dtype=np.float64)
for d in range(1, 367):
    if d == 60: continue
    idx = np.where(masks[d])[0]
    pool = ext[idx]
    allnan = np.all(np.isnan(pool), axis=0)
    psafe = np.where(allnan, 0.0, pool)
    thr[d] = np.quantile(psafe, 0.9, method='hazen', axis=0)
    thr[d] = np.where(allnan, np.nan, thr[d])
    s = np.nansum(psafe, axis=0); c = np.count_nonzero(~allnan, axis=0)
    cli[d] = np.where(c > 0, s / np.maximum(c, 1), np.nan)
thr[60] = 0.5 * (thr[59] + thr[61])
cli[60] = 0.5 * (cli[59] + cli[61])
print("pre-smooth thr nan cells:", np.isnan(thr[1:]).sum(), "cli nan:", np.isnan(cli[1:]).sum())

def smooth31(X):
    acc = np.zeros_like(X); cnt = np.zeros_like(X)
    for k in range(-15, 16):
        R = np.roll(X, k, axis=0)
        acc += np.where(np.isnan(R), 0.0, R)
        cnt += (~np.isnan(R))
    return np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan)

thr_s = smooth31(thr)
cli_s = smooth31(cli)
print("smoothed thr nan (d1..366):", np.isnan(thr_s[1:]).sum(), "cli_s nan:", np.isnan(cli_s[1:]).sum())
np.savez_compressed('/work/thr_cli.npz', thr=thr, cli=cli, thr_s=thr_s, cli_s=cli_s,
                    dates=np.array(dates), doy_all=doy_all)
print("saved")
c = (30, 30)
print("sample thr_s at d153,183,214:", thr_s[[153,183,214], c[0], c[1]])
print("sample cli_s:", cli_s[[153,183,214], c[0], c[1]])
