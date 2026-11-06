import numpy as np, pandas as pd

sst_base = np.load('/work/sst_base.npy')  # just to have same env
base_dates = pd.read_pickle('/work/base_dates.pkl')

CUM = np.array([0,31,59,90,120,151,181,212,243,273,304,334])
def map_doy(ts):
    return int(CUM[ts.month-1] + ts.day + (1 if ts.month > 2 else 0))

base_doy = np.array([map_doy(ts) for ts in base_dates])
n = len(base_dates)
pool = np.zeros((367, n), dtype=bool)
anchor_mask = (base_dates >= '1992-01-01') & (base_dates <= '2002-12-31') & (base_doy != 60)
anchors = np.where(anchor_mask)[0]
print("n anchors:", anchors.size)
cnt = np.bincount(base_doy[anchors], minlength=367)
print("anchors per doy 55-66:", cnt[55:67])
for k in anchors:
    d = base_doy[k]
    pool[d, max(0,k-5):min(n,k+6)] = True
sizes = pool.sum(axis=1)          # sizes[d] = pool size of doy d (index=d)
print("pool sizes doy 54-67:", {int(d): int(sizes[d]) for d in range(54,68)})
print("pool size doy 60 (Feb29):", int(sizes[60]))
print("unique pool sizes (doy 1..366):", sorted(set(int(x) for x in sizes[1:])))
# verify Feb 29 1992 is inside pool 59 and 61 windows
i_feb29 = int(np.where(base_dates == '1992-02-29')[0][0])
print("1992-02-29 in pool59:", bool(pool[59, i_feb29]), "| in pool61:", bool(pool[61, i_feb29]),
      "| in pool60 (should be False):", bool(pool[60, i_feb29]))
# verify window membership example: 1992-03-05 in pool 59, 1992-02-23 in pool 59
for ds in ['1992-02-23','1992-03-05','1996-02-29','2000-03-01']:
    ii = int(np.where(base_dates == ds)[0][0])
    in59 = bool(pool[59, ii]); in61 = bool(pool[61, ii])
    print(f"{ds}: pool59={in59} pool61={in61}")
