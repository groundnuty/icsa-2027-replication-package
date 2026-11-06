import numpy as np, datetime as dt, time
data = np.load('/work/S.npz', allow_pickle=True)
S_base = data['S_base']; S_tgt = data['S_tgt']
dates = [dt.date.fromisoformat(s) for s in data['dates']]
tgt_dates = dates[4028:]
sea = np.isfinite(S_tgt).all(axis=0)
St = S_tgt[:, sea].astype(np.float64)
tc = np.load('/work/thrclim.npz')
THR, CLIM = tc['THR'], tc['CLIM']

def doy(d):
    return (d.replace(year=2020) - dt.date(2020,1,1)).days + 1

def smooth366(arr):
    # arr: (366, C); out[d] = mean of arr[(d-15 .. d+15) mod 366]
    pad = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)   # (396, C)
    cs = np.concatenate([np.zeros((1, arr.shape[1])), np.cumsum(pad, axis=0)], axis=0)
    return (cs[31:] - cs[:-31]) / 31.0

t0=time.time()
THR_s = smooth366(THR)
CLIM_s = smooth366(CLIM)
print("smooth done", time.time()-t0)

# verify smoothing manually for a few cells
rng = np.random.default_rng(2)
for it in range(5):
    c = int(rng.integers(3311)); i = int(rng.integers(366))
    ref = np.mean([THR[(i+j) % 366, c] for j in range(-15, 16)])
    assert np.allclose(THR_s[i, c], ref), (i, c, ref, THR_s[i,c])
print("smoothing verified")

# target doys
tgt_doy = np.array([doy(d) for d in tgt_dates])
print("target doy range:", tgt_doy.min(), tgt_doy.max(), "first/last:", tgt_dates[0], tgt_doy[0], tgt_dates[-1], tgt_doy[-1])

# hot days: SST >= threshold (float64, kelvin as stored)
THR_t = THR_s[tgt_doy - 1]                    # (92, 3311)
hot = St >= THR_t
print("hot days total:", hot.sum(), "max per day:", hot.sum(axis=1).max())

# per-cell MHWs: runs >=5, join gaps of 1-2 non-hot days (gap days included)
mask = np.zeros((92, 3311), dtype=np.uint8)
runs_info = []
for c in range(3311):
    h = hot[:, c]
    pad = np.concatenate([[False], h, [False]])
    starts = np.flatnonzero(~pad[:-1] & pad[1:])
    ends   = np.flatnonzero(pad[:-1] & ~pad[1:]) - 1
    # keep runs of length >=5
    keep = [(s, e) for s, e in zip(starts, ends) if (e - s + 1) >= 5]
    if not keep: continue
    # join runs separated by 1-2 non-hot days
    groups = [[keep[0]]]
    for s, e in keep[1:]:
        prev_e = groups[-1][-1][1]
        gap = s - prev_e - 1
        if gap <= 2:
            groups[-1].append((s, e))
        else:
            groups.append([(s, e)])
    for g in groups:
        s0, e0 = g[0][0], g[-1][1]
        mask[s0:e0+1, c] = 1
        runs_info.append((c, s0, e0))
print("per-cell MHWs (merged):", len(runs_info))
active = mask.any(axis=1)
print("active days:", int(active.sum()), "of 92")
print("mask sum:", int(mask.sum()))
np.savez_compressed('/work/mask.npz', mask=mask, active=active,
                    tgt_dates=[d.isoformat() for d in tgt_dates],
                    reg_lat=data['reg_lat'], reg_lon=data['reg_lon'])
# regional events
ev = []
in_ev = False
for i, a in enumerate(active):
    if a and not in_ev:
        s = i; in_ev = True
    elif not a and in_ev:
        ev.append((s, i-1)); in_ev = False
if in_ev: ev.append((s, len(active)-1))
print("regional events:", [(tgt_dates[a], tgt_dates[b], b-a+1) for a,b in ev])
