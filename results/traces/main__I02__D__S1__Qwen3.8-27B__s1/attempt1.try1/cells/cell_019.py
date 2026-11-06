import numpy as np, datetime as dt
S_base = np.load('/work/S_base.npy')
cr = np.load('/work/coords.npz'); lat, lon = cr['lat'], cr['lon']
base_dates = [dt.date.fromisoformat(str(d)) for d in cr['baseline_dates'].astype('datetime64[D]').astype(object)]
# cell 0 = row0,col0 -> lat[0]=54.18, lon[0]=13.26
c0 = 0
fin = np.isfinite(S_base[:, c0]).sum()
print("cell0 finite days in base window:", fin, "of", len(base_dates))
# show a few summer values
for i, d in enumerate(base_dates):
    if d.month == 6 and d.day == 15 and d.year in (1992, 1995, 2000, 2002):
        print(d, S_base[i, c0])
# compare with a middle cell, e.g. row 30 col 30 (idx 30*60+30=1830)
c1 = 30*60+30
print("cell(30,30) lat/lon:", lat[30], lon[30], "finite base days:", np.isfinite(S_base[:, c1]).sum())
# and its value 2000-06-15
i = base_dates.index(dt.date(2000,6,15))
print("2000-06-15:", S_base[i, c1])
# per-cell finite-day histogram: how many cells have <100 finite base days
finall = np.isfinite(S_base).sum(axis=0)
print("cells with 0 finite base days:", (finall==0).sum())
print("cells with <100:", (finall<100).sum())
# which cells have 0?
zero = np.where(finall==0)[0]
print("zero cells:", zero[:20], "count", zero.size)
