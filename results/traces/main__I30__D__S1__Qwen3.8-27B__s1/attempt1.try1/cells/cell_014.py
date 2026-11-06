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

d = 153
ib = b_idx[b_doy == d]
starts = np.clip(ib-5, 0, ext_n-1); ends = np.clip(ib+5,0,ext_n-1)+1
m = np.zeros(ext_n+1, np.int32); np.add.at(m, starts, 1); np.add.at(m, ends, -1)
mask = np.cumsum(m)[:-1] > 0
idx = np.where(mask)[0]
col = ext[idx, 22, 4]
print("d=153 pool size:", len(idx), "all NaN:", np.all(np.isnan(col)))
tc = np.load('/work/thr_cli.npz', allow_pickle=False)
thr, cli = tc['thr'], tc['cli']
print("saved thr[153,22,4]:", thr[153,22,4], " saved cli[153,22,4]:", cli[153,22,4])
print("saved cli[153,30,30]:", cli[153,30,30], " saved thr[153,30,30]:", thr[153,30,30])
allnan = np.all(np.isnan(ext[idx]), axis=0)
psafe = np.where(allnan, 0.0, ext[idx])
s = np.nansum(psafe, axis=0); c = np.count_nonzero(~allnan, axis=0)
out = np.where(c > 0, s / np.maximum(c, 1), np.nan)
print("recomputed cli[22,4]:", out[22,4], " [30,30]:", out[30,30])
print("allnan[22,4]:", allnan[22,4], " c[22,4]:", c[22,4])
