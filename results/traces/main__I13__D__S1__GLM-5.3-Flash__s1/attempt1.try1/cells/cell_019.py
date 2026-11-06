import numpy as np, datetime as dt, json, time, warnings
warnings.filterwarnings('ignore')

# ---- load extracted data ----
datestrs = np.load('/work/extract_dates.npy')
arr32 = np.load('/work/extract_sst.npy')   # (4120, 60, 60) float32
dates = [dt.date.fromisoformat(s) for s in datestrs]
n_base_win = sum(1 for d in dates if d <= dt.date(2003,1,5))
print('baseline-window days:', n_base_win, 'first:', dates[0], 'last baseline-window:', dates[n_base_win-1])
base_win_dates = dates[:n_base_win]
tgt_dates = dates[n_base_win:]
print('target:', tgt_dates[0], '..', tgt_dates[-1], len(tgt_dates))

date_to_idx = {d: i for i, d in enumerate(base_win_dates)}

# ---- DOY mapping helpers (special 1..366 mapping; non-leap years have no day 60) ----
def mapped_doy(d):
    if d.month <= 2:
        return (d - dt.date(d.year,1,1)).days + 1
    leap = (d.year%4==0 and (d.year%100!=0 or d.year%400==0))
    doy_cal = (d - dt.date(d.year,1,1)).days + 1
    return doy_cal + (0 if leap else 1)

def date_of_doy(year, doy):
    leap = (year%4==0 and (year%100!=0 or year%400==0))
    if doy <= 59:
        return dt.date(year,1,1) + dt.timedelta(days=doy-1)
    if doy == 60:
        return dt.date(year,2,29) if leap else None
    return dt.date(year,3,1) + dt.timedelta(days=doy-61)

# sanity
print('mapped_doy checks:', mapped_doy(dt.date(1992,2,29)), mapped_doy(dt.date(1992,3,1)),
      mapped_doy(dt.date(1993,2,28)), mapped_doy(dt.date(1993,3,1)), mapped_doy(dt.date(1992,12,31)),
      mapped_doy(dt.date(1993,12,31)), mapped_doy(dt.date(2021,6,1)), mapped_doy(dt.date(2021,8,31)))

# ---- build pools per DOY ----
arr_base64 = arr32[:n_base_win].astype(np.float64)
pools = {}  # doy -> index array into base window
for doy in range(1, 367):
    if doy == 60: continue
    idxs = []
    for year in range(1992, 2003):
        bd = date_of_doy(year, doy)
        if bd is None: continue
        for off in range(-5, 6):
            dd = bd + dt.timedelta(days=off)
            j = date_to_idx.get(dd)
            if j is not None:
                idxs.append(j)
    pools[doy] = np.array(sorted(set(idxs)))
sizes = np.array([len(v) for v in pools.values()])
print('pool sizes: min', sizes.min(), 'max', sizes.max())
print('doy 1 pool first/last dates:', base_win_dates[pools[1][0]], base_win_dates[pools[1][-1]])
print('doy 365 pool first/last dates:', base_win_dates[pools[365][0]], base_win_dates[pools[365][-1]])
print('doy 366 pool dates count:', len(pools[366]), 'years covered:', sorted(set(base_win_dates[i].year for i in pools[366])))
np.save('/work/pool_sizes.npy', sizes)
