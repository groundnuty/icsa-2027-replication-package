import numpy as np, datetime as dt, calendar
sst = np.load('/work/sst_cube.npy')
times = np.load('/work/times.npy').astype('datetime64[D]')
print(sst.shape, times[0], times[-1])

# doy mapping: Jan1=1..Feb28=59, Feb29=60, Mar1=61 ...
def dayofyear(d: dt.date) -> int:
    if d.month == 2 and d.day == 29:
        return 60
    return sum([31,28,31,30,31,30,31,31,30,31,30,31][:d.month-1]) + d.day

# sanity
for d, exp in [(dt.date(1992,1,1),1),(dt.date(1992,2,28),59),(dt.date(1992,2,29),60),(dt.date(1992,3,1),61),
               (dt.date(2001,12,31),365),(dt.date(2002,12,31),366)]:
    print(d, dayofyear(d), "exp", exp)
assert dayofyear(dt.date(2001,12,31)) == 365 and dayofyear(dt.date(2002,12,31)) == 366

# verify file dates match loaded times
dates = [dt.date(1991,12,27)+dt.timedelta(days=k) for k in range(4010)]
dates += [dt.date(2012,6,1)+dt.timedelta(days=k) for k in range(92)]
assert len(dates) == sst.shape[0]
ok = all(times[k] == np.datetime64(dates[k]) for k in [0,1,4009,4010,4119])
print("dates-vs-times spot ok:", ok)

# sea mask: finite on every target day
t0 = dt.date(2012,6,1); t1 = dt.date(2012,8,31)
idx_t0 = dates.index(t0); idx_t1 = dates.index(t1)
print("target idx:", idx_t0, idx_t1)
target_finite = np.isfinite(sst[idx_t0:idx_t1+1])
sea = target_finite.all(axis=0)
print("sea cells:", int(sea.sum()))
np.save('/work/sea_mask.npy', sea)

# check baseline availability per sea cell: count NaN in baseline per cell (diagnostic only)
base_sl = slice(0, 4010)
base_dates = dates[:4010]
doys = np.array([dayofyear(d) for d in base_dates])
in_base = np.array([(1992 <= d.year <= 2002) for d in base_dates])
print("baseline days loaded:", int(in_base.sum()), "(expect 4018)")
