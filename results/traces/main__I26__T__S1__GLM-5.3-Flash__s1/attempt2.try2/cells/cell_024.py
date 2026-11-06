import numpy as np, json, datetime as dt

dates = json.load(open('cache/dates.json'))
tgt_s = dates['tgt_s']
SST_t = np.load('cache/SST_t.npy')      # (92,60,60) float64
thr_s = np.load('cache/thr_s.npy')      # (366,60,60)
clim_s = np.load('cache/clim_s.npy')
sea = np.load('cache/sea.npy')          # (60,60) bool
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
doy_tgt = np.array([cum[d.month-1]+d.day for d in [dt.date(int(s[:4]),int(s[4:6]),int(s[6:8])) for s in tgt_s]])

# sanity: verify nanquantile(method='hazen') == manual Hyndman-Fan type 5 on a sample pool
rng = np.random.default_rng(0)
pool = rng.normal(size=121); pool[3]=np.nan
q_np = np.nanquantile(pool, 0.9, method='hazen')
xs = np.sort(pool[~np.isnan(pool)]); n=len(xs); h=n*0.9+0.5
lo,hi=int(np.floor(h)),int(np.ceil(h))
q_man = xs[lo-1] + (h-lo)*(xs[hi-1]-xs[lo-1])
print('quantile check:', q_np, q_man, np.isclose(q_np,q_man))

# hot days: SST >= threshold for that cell & doy  (target period only)
thr_t = thr_s[doy_tgt-1]                # (92,60,60)
hot = np.zeros(SST_t.shape, dtype=bool)
fin = np.isfinite(SST_t) & np.isfinite(thr_t)
hot[fin] = SST_t[fin] >= thr_t[fin]
print('hot days total:', int(hot[:,sea].sum()), 'of', int(sea.sum())*92)
print('hot frac per target day (sea):', np.round(hot[:,sea].mean(axis=1),3))

# per-cell MHW detection with joining
T, NY, NX = hot.shape
mhw = np.zeros(hot.shape, dtype=np.uint8)
nseg_kept = 0; nseg_final = 0
for i in range(NY):
    for j in range(NX):
        if not sea[i,j]:
            continue
        h = hot[:,i,j]
        idx = np.where(h)[0]
        if idx.size == 0:
            continue
        # maximal hot runs
        breaks = np.where(np.diff(idx) > 1)[0]
        starts = np.r_[idx[0], idx[breaks+1]]
        ends   = np.r_[idx[breaks], idx[-1]]
        lens = ends - starts + 1
        keep = lens >= 5
        if not keep.any():
            continue
        s_list = starts[keep]; e_list = ends[keep]
        nseg_kept += len(s_list)
        # join segments separated by 1-2 non-hot days
        cs = s_list[0]; ce = e_list[0]
        for k in range(1, len(s_list)):
            s2, e2 = s_list[k], e_list[k]
            gap = s2 - ce - 1
            if gap <= 2:
                ce = e2
            else:
                mhw[cs:ce+1, i, j] = 1
                nseg_final += 1
                cs, ce = s2, e2
        mhw[cs:ce+1, i, j] = 1
        nseg_final += 1
print('kept hot runs (>=5d):', nseg_kept, ' final per-cell MHW segments after joining:', nseg_final)
np.save('cache/mhw.npy', mhw)

# regional: active if any sea cell in MHW that day
active = mhw[:, sea].any(axis=1)
print('active days:', int(active.sum()), 'of', T)
runs = []
idx = np.where(active)[0]
if idx.size:
    br = np.where(np.diff(idx) > 1)[0]
    st = np.r_[idx[0], idx[br+1]]; en = np.r_[idx[br], idx[-1]]
    runs = list(zip(st.tolist(), en.tolist()))
def dstr(s): return f'{s[:4]}-{s[4:6]}-{s[6:]}'
events = [{'onset': dstr(tgt_s[a]), 'end': dstr(tgt_s[b])} for a,b in runs]
print('regional events:', events)
for a,b in runs:
    print(f'  {dstr(tgt_s[a])} .. {dstr(tgt_s[b])}  len={b-a+1}d')
# per-day active cell counts
print('active cells per day:', active.astype(int)* (mhw[:,sea].sum(axis=1)))
json.dump(events, open('cache/events.json','w'))
