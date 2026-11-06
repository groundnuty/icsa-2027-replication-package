import numpy as np, pandas as pd, os, json

# --- synthetic tests of run/join logic ---
def runs_of(h, T):
    hh = h.astype(np.int8); d = np.diff(hh)
    starts = list(np.where(d == 1)[0] + 1); ends = list(np.where(d == -1)[0])
    if hh[0] == 1: starts = [0] + starts
    if hh[-1] == 1: ends = ends + [T-1]
    return list(zip(starts, ends))

def detect(h):
    T = len(h)
    kept = [(s, e) for (s, e) in runs_of(h, T) if e-s+1 >= 5]
    if not kept: return []
    ev = []
    for (s, e) in kept:
        if ev and (s - ev[-1][1] - 1) <= 2: ev[-1] = (ev[-1][0], e)
        else: ev.append((s, e))
    return ev

tests = [
    ([1]*6 + [0] + [1]*5, [(0, 11)]),                 # 1-day gap joined
    ([1]*5 + [0,0] + [1]*5, [(0, 11)]),               # 2-day gap joined
    ([1]*5 + [0,0,0] + [1]*5, [(0,4), (8,12)]),       # 3-day gap NOT joined
    ([1]*4 + [0] + [1]*6, [(5, 10)]),                 # 4-day run discarded
    ([1]*5 + [0] + [1]*3 + [0] + [1]*5, [(0,4), (10,14)]),  # short run not bridging
    ([1]*5, [(0,4)]), [0]*12 and ([0]*12, []),        # exact 5
]
for h, exp in tests:
    got = detect(np.array(h, dtype=bool))
    print("ok" if got == exp else "FAIL", got, "expected", exp)

# --- event boundary checks on real result ---
mhw = np.load("/work/mhw.npy"); sea = np.load("/work/sea.npy")
import xarray as xr
ds = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", engine="h5netcdf")
times = pd.DatetimeIndex(ds["time"].values)
ti = np.where((times >= "2014-06-01") & (times <= "2014-08-31"))[0]
tdates = times[ti]
active = mhw[:, sea].any(axis=1)
print("active runs:", runs_of(active, len(ti)))
print("active on 07-23:", bool(active[tdates.get_loc(pd.Timestamp('2014-07-23'))]),
      "| 07-24:", bool(active[tdates.get_loc(pd.Timestamp('2014-07-24'))]),
      "| 08-18:", bool(active[tdates.get_loc(pd.Timestamp('2014-08-18'))]),
      "| 08-19:", bool(active[tdates.get_loc(pd.Timestamp('2014-08-19'))]))
perday = mhw[:, sea].sum(axis=1)
for d in range(0, 92, 5):
    print(tdates[d].date(), int(perday[d]))
print(tdates[-1].date(), int(perday[-1]))
print("max cells active/day:", int(perday.max()), "min in event:", int(perday[tdates.get_loc(pd.Timestamp('2014-07-24')):tdates.get_loc(pd.Timestamp('2014-08-18'))+1].min()))

# --- filesystem ---
for root in ["/", "/work"]:
    try: print(root, "->", sorted(os.listdir(root))[:30])
    except Exception as e: print(root, e)
print("/work/output exists:", os.path.isdir("/work/output"))
