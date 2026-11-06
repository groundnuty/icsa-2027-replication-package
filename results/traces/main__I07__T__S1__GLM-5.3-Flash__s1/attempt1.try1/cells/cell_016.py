import numpy as np, datetime as dt
mhw = np.load('/tmp/mhw_result.npz')['mhw']
z = np.load('/tmp/region_cube.npz', allow_pickle=True)
BLK = 4028
dates = [dt.datetime.strptime(str(s), '%Y%m%d').date() for s in z['dates'][BLK:]]
active = mhw.any(axis=1)
print("counts per day (only days with mhw>0 shown compactly):")
zero_days = [str(d) for i,d in enumerate(dates) if not active[i]]
print("inactive days:", zero_days)
# confirm event boundaries
idx_act = np.where(active)[0]
print("first active:", dates[idx_act[0]], "last active:", dates[idx_act[-1]], "n:", len(idx_act))
print("consecutive check:", np.all(np.diff(idx_act)==1))
