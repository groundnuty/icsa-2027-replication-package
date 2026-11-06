import numpy as np, pickle, time
with open("/tmp/data.pkl","rb") as f:
    D = pickle.load(f)
data = D["data"]; i0,i1,j0,j1 = D["i0"],D["i1"],D["j0"],D["j1"]

# --- sea cells: finite on every day of target period 2005-06-01..2005-08-31 ---
yr = data[2005]
target_idx = np.where((np.arange(np.datetime64('2005-01-01').astype(int), np.datetime64('2006-01-01').astype(int)) >= np.datetime64('2005-06-01').astype(int)) & (np.arange(np.datetime64('2005-01-01').astype(int), np.datetime64('2006-01-01').astype(int)) < np.datetime64('2005-09-01').astype(int)))[0]
print("target days in 2005:", target_idx.size, target_idx[0], target_idx[-1])
fin_all = np.all(np.isfinite(yr[target_idx]), axis=0)
print("sea cells:", fin_all.sum(), "of", fin_all.size)

# --- day-of-year mapping (1..366, leap-aware: 29 Feb = 60) ---
def doy_map(dates):
    d = dates.astype('datetime64[D]')
    y = d.astype('datetime64[Y]').astype(int) + 1970
    start = (d.astype('datetime64[M]') - d.astype('datetime64[Y]')).astype(int)  # month index 0..11
    def days_before_month(y, m):
        cum = [0,31,59,90,120,151,181,212,243,273,304,334]
        n = cum[m]
        if m >= 2 and (y%4==0 and (y%100!=0 or y%400==0)): n += 1
        return n
    dd = (d - d.astype('datetime64[M]') + np.timedelta64(1,'D')).astype(int)  # day of month
    return np.array([days_before_month(yy, mm) + ddm for yy, mm, ddm in zip(y, start, dd)])

# baseline dates 1991..2003 present in data
years = sorted(data.keys())
all_dates = []
all_doy = []
for y in years:
    nd = data[y].shape[0]
    dates = np.arange(np.datetime64(f"{y}-01-01"), np.datetime64(f"{y}-01-01") + np.timedelta64(nd,'D'))
    all_dates.append(dates); all_doy.append(doy_map(dates))
dates = np.concatenate(all_dates); doys = np.concatenate(all_doy)
years_arr = np.concatenate([np.full(data[y].shape[0], y) for y in years])
print("baseline+spill days:", dates.size, dates[0], dates[-1])

# --- build pools per (day-of-year, cell): pooled values per doy across baseline years ---
# For each doy d (1..366, d!=60), pool = values on dates within +-5 calendar days of any baseline date with doy==d.
# Equivalent: for each date in 1991..2003 with doy != 60, it belongs to the pools of doys d such that
# the date is within 5 days of some baseline date with doy d. Simpler: iterate over dates, add each date's
# values to pool of its own doy; also, for dates with doy 59 and 61 handle Feb 29 adjacency; and windows
# reaching past ends are covered by including 1991 & 2003 data (we already loaded those years).
# But windows near ends: e.g. doy 1 (Jan 1) windows 1991-12-27..1992-01-05 -> includes 1991 Dec days; fine, we have 1991.
# For doy 366: pool includes dates within 5 days of any Dec 31 (doy 366) baseline date: 2003-12-26..2003-12-31 etc.
# Feb 29 (doy 60) dates: belong to windows of calendar neighbours. Which doys get them? For baseline dates with
# doy d, the window is [date-5, date+5]. Feb 29 date has doy 60 (no pool). But is Feb 29 within the window of a
# doy-59 (Feb 28) date? Yes: Feb 29 is 1 day after Feb 28, within 5 days. Also within window of doy-61 (Mar 1) date
# (1 day before). And any d whose baseline dates are within 5 days of Feb 29: doy 55..65 in leap years and
# doy 55..64/56..65 in non-leap... Precisely: Feb 29 is within 5 calendar days of dates with doy 55..64 (leap yrs)
# and doy 55..64 in non-leap? Non-leap: Mar 1 = doy 60, Mar 2 = 61 ... Feb 29 is 1 day before Mar 1, so within
# windows of non-leap doys 60..65 -> but in non-leap years doy 60 = Mar 1, doy 61 = Mar 2 etc.
# So the pools mix leap/non-leap calendar neighbours naturally. Let me just do it directly:
# For each doy d in 1..366, d != 60: find all baseline dates with doy == d (in any baseline year 1992..2002);
# for each such date, window = date +- 5 days; collect values of all dates in 1991..2003 within those windows.
# Efficient approach: for each date in 1991..2003, determine set of doys d for which this date is in the window.
# A date X is in the window of baseline date B (doy d) iff |X - B| <= 5 days. So doys d of X's membership =
# {doy(B) : B baseline date (1992..2002), |X-B| <= 5}. For X's own year in 1992..2002: includes doy(X) itself
# (its own doy, if != 60). For other years: includes doys of nearby dates in those years.
# Simplest correct: for each doy d (1..366, d!=60), get all baseline dates with that doy; then window mask on
# the 1991..2003 date array = OR over those dates of (|dates - bdate| <= 5). 366 iterations, each cheap.
N = dates.size
t0 = time.time()
pool_doys = []
for d in range(1, 367):
    if d == 60:
        pool_doys.append(None); continue
    bdates = dates[(years_arr >= 1992) & (years_arr <= 2002) & (doys == d)]
    # window mask
    mask = np.zeros(N, dtype=bool)
    for b in bdates:
        mask |= (np.abs((dates - b).astype(int)) <= 5)
    pool_doys.append(mask)
print("pool masks built %.1fs" % (time.time()-t0))
# sanity: check doy 1 mask count and doy 60 is None
print("doy1 pool days:", pool_doys[0].sum(), "doy59:", pool_doys[58].sum(), "doy61:", pool_doys[60].sum(), "doy366:", pool_doys[365].sum())
# check that Feb 29 dates are included in doy 59 and 61 pools
feb29_mask = (dates.astype('datetime64[M]').astype(int) == 1) & (dates.astype('datetime64[D]').astype(int) == 29)
print("feb29 dates:", dates[feb29_mask])
print("feb29 in doy59 pool:", pool_doys[58][feb29_mask], "in doy61 pool:", pool_doys[60][feb29_mask])
with open("/tmp/pools.pkl","wb") as f:
    pickle.dump({"pool_doys": pool_doys, "dates": dates, "doys": doys, "years_arr": years_arr,
                 "sea": fin_all, "target_idx": target_idx}, f, protocol=4)
print("saved")
