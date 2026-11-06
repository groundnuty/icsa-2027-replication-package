import numpy as np
# compare edge-day thresholds: recompute quick with modular pools for doy 1, 366 only
block = np.load("/tmp/sst_block.npy")
alldays = open("/tmp/alldays.txt").read().split("\n")
nb = 4028
base = block[:nb].astype(np.float64)
cum_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_of(s):
    m, d = int(s[5:7]), int(s[8:10]); return cum_before[m-1] + d
doy = np.array([doy_of(s) for s in alldays[:nb]])
def hazen_nanperc(A, p=0.9):
    n = A.shape[0]; flat = A.reshape(n, -1); s = np.sort(flat, axis=0)
    k = n - np.isnan(s).sum(axis=0)
    kk = np.where(k>0, k, 1).astype(float)
    h = kk*p + 0.5; j = np.floor(h).astype(int); g = h - j
    j0 = np.clip(j,1,kk.astype(int))-1; jp = np.clip(j+1,1,kk.astype(int))-1
    idx = np.arange(flat.shape[1])
    res = s[j0, idx] + g*(s[jp, idx]-s[j0, idx])
    out = np.full(flat.shape[1:], np.nan); ok = k>0
    out[ok] = res[ok]; return out.reshape(A.shape[1:])

for d in (1, 366):
    dist = np.abs(doy - d); dist = np.minimum(dist, 366-dist)
    mod = (doy != 60) & (dist <= 5)
    raw_mod = hazen_nanperc(base[mod])[0]
    # calendar from raw_thr saved earlier
    raw_cal = np.load("/tmp/raw_thr.npy")[d-1]
    diff = np.abs(raw_mod - raw_cal)
    print(f"doy {d}: modular n={mod.sum()}, calendar n=121, max|diff|={np.nanmax(diff):.6f} K, n cells differing={np.sum(diff>0)}")

# now rerun steps 3-4 with corrected thresholds
sea_cells = np.load("/tmp/sea_cells.npy")
thr = np.load("/tmp/thr_smooth.npy")
target_days = alldays[nb:]
nt = len(target_days)
sst = block[nb:].astype(np.float64)
tdoy = np.array([doy_of(s) for s in target_days])
print("target doys:", tdoy[0], "..", tdoy[-1])
thr_t = thr[tdoy - 1]
hot = sst >= thr_t
hot[:, ~sea_cells] = False
mhw = np.zeros_like(hot)
flat_hot = hot.reshape(nt, -1); flat_mhw = mhw.reshape(nt, -1)
nruns=0; njoins=0
for c in range(flat_hot.shape[1]):
    seq = flat_hot[:, c]
    if not seq.any(): continue
    idx = np.flatnonzero(np.diff(np.concatenate(([False], seq, [False])).astype(np.int8)))
    starts = idx[0::2]; ends = idx[1::2]-1
    keep=[]
    for s,e in zip(starts,ends):
        if e-s+1 >= 5:
            if keep and s - keep[-1][1] - 1 <= 2:
                keep[-1][1] = e; njoins += 1
            else:
                keep.append([s,e]); nruns += 1
    for s,e in keep: flat_mhw[s:e+1, c] = True
print("per-cell runs(>=5d):", nruns, "joins:", njoins)
active = flat_mhw.any(axis=1)
print("active days:", int(active.sum()), "of", nt)
ev=[]; i=0
while i < nt:
    if active[i]:
        j=i
        while j+1<nt and active[j+1]: j+=1
        ev.append((target_days[i], target_days[j])); i=j+1
    else: i+=1
print("regional events:", ev)
for s,e in ev:
    print(s, "->", e, "length", (date.fromisoformat(e)-date.fromisoformat(s)).days+1)
np.save("/tmp/mhw_mask.npy", mhw)
with open("/tmp/events.txt","w") as fh: fh.write("\n".join(f"{s} {e}" for s,e in ev))
print("hot frac:", hot.mean(), "| mhw frac:", mhw.mean())
