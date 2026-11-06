import numpy as np, json, datetime as dt, os
print("cwd:", os.getcwd())
print("writable test:", end=" ")
try:
    os.makedirs("output", exist_ok=True)
    with open("output/.t","w") as f: f.write("x")
    os.remove("output/.t")
    print("ok -> relative ./output")
except Exception as e:
    print("fail", e)

OUT="/tmp/mhw"
tgt = np.load(f"{OUT}/tgt.npy").reshape(92, 3600)
thr_s = np.load(f"{OUT}/thr_s.npy")
sea = np.load(f"{OUT}/sea.npy")
D_tgt = np.load(f"{OUT}/D_tgt.npy")
dates = json.load(open(f"{OUT}/dates.json"))
tgt_dates = [dt.date.fromisoformat(s) for s in dates["tgt_dates"]]

hot = (tgt >= thr_s[D_tgt]) & sea[None,:]
per_day = hot.sum(axis=1)
print("hot cells per day (every 5th day):")
for i in range(0, 92, 5):
    print(tgt_dates[i], int(per_day[i]))
print("max per day:", int(per_day.max()))

# per-cell hot counts and max run
sea_idx = np.flatnonzero(sea)
hc = hot[:, sea_idx].sum(axis=0)
print("cells with any hot day:", int((hc>0).sum()), "max hot days in a cell:", int(hc.max()))

def maxrun(h):
    best=cur=0
    for v in h:
        cur = cur+1 if v else 0
        best=max(best,cur)
    return best
mr = np.array([maxrun(hot[:, c]) for c in sea_idx])
print("max run length distribution:", {l:int((mr==l).sum()) for l in np.unique(mr)})

# look at one cell with hot days
c = int(sea_idx[np.argmax(hc)])
print("cell", c, "hot days:", hc.max())
i = c//60; j = c%60
lat = np.load(f"{OUT}/lat.npy"); lon = np.load(f"{OUT}/lon.npy")
print("lat,lon:", lat[i], lon[j])
sub = tgt[:, c] - thr_s[D_tgt, c]
print("sst-thr series (K), rounded:")
for k in range(0, 92, 4):
    print(tgt_dates[k], round(float(sub[k]),3), "hot" if hot[k,c] else "")
print("min margin:", float(np.nanmin(sub)), "max margin:", float(np.nanmax(sub)))
