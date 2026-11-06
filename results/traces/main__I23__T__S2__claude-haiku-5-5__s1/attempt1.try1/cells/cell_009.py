
def fix_smooth(arr):
    a = arr.copy()
    a[60] = 0.5*(a[59]+a[61])
    x = a[1:367]  # 366 elements, index 0 = day1
    out = np.empty_like(x)
    n=366
    for d in range(n):
        idx = [((d+k) % n) for k in range(-15,16)]
        out[d] = x[idx].mean(axis=0)
    res = np.full_like(arr, np.nan); res[1:367]=out
    return res
thr_s = fix_smooth(thr)
clim_s = fix_smooth(clim)
tdoy = doy(tt)
T = thr_s[tdoy]  # (ntime,60,60)
hot = (tvals >= T) & sea[None]
nt, ny, nx = hot.shape
mhw = np.zeros_like(hot, dtype=np.uint8)
for i in range(ny):
    for j in range(nx):
        if not sea[i,j]: continue
        h = hot[:,i,j]
        # runs of hot days length>=5
        runs=[]; t=0
        while t<nt:
            if h[t]:
                s=t
                while t<nt and h[t]: t+=1
                if t-s>=5: runs.append([s,t-1])
            else: t+=1
        if not runs: continue
        # join runs separated by 1-2 non-hot days
        merged=[runs[0]]
        for r in runs[1:]:
            gap = r[0]-merged[-1][1]-1
            if gap<=2: merged[-1][1]=r[1]
            else: merged.append(r)
        for s,e in merged: mhw[s:e+1,i,j]=1
active = mhw.any(axis=(1,2))
events=[]; t=0
while t<nt:
    if active[t]:
        s=t
        while t<nt and active[t]: t+=1
        events.append({"onset": str(tt[s].date()), "end": str(tt[t-1].date())})
    else: t+=1
print(events, mhw.sum(), active.sum(), sea.sum())
