import numpy as np, pickle, time
from datetime import date, timedelta

arr = np.load("/work/baseline_region_f32.npy")
data = arr.astype(np.float64)
d0 = date(1991,12,27)
date_list = [d0 + timedelta(days=k) for k in range(arr.shape[0])]
def doy_of(dt): return (dt - date(dt.year,1,1)).days + 1
base_idx = {d: k for k, d in enumerate(date_list)}
base_dates = [d for d in date_list if date(1992,1,1) <= d <= date(2002,12,31)]

# exact pools (build again, save indices)
pool_idx = {}
for d in range(1, 367):
    if d == 60: continue
    win = set()
    for b in base_dates:
        if doy_of(b) == d:
            k = base_idx[b]
            for kk in range(max(0,k-5), min(arr.shape[0], k+6)):
                win.add(kk)
    pool_idx[d] = sorted(win)

# compare with old approach: old = dates whose doy in [d-5, d+5] & != 60
# (old win_dates stored date objects)
with open("/work/window_dates.pkl","rb") as f:
    wd_old = pickle.load(f)
win_old = wd_old["win_dates"]

print("d=366 new size:", len(pool_idx[366]))
print("d=366 new dates:", [date_list[k] for k in pool_idx[366]][:10], "...", [date_list[k] for k in pool_idx[366]][-5:])
# d=366 pool should be: baseline dates with doy 366 (1992-12-31..2002-12-31, 11 dates) +/- 5 calendar days
# -> windows reach into Jan 1993 (doy 1-5 of 1993)? b+5 for b=2002-12-31 -> 2003-01-05 (in array). 
# So new should have ~11*11=121 - but only 33?
# Check: doy 366 = 31 Dec only (leap years). Baseline years 1992..2002: leap years 1992, 1996, 2000 -> Dec 31 doy 366 in all years (Dec 31 is doy 366 regardless of leap year!)
# Wait: Dec 31 1992 doy=366 (leap). Dec 31 1993 doy=365! (non-leap). So baseline dates with doy 366 are only 1992,1996,2000 -> 3 dates
# windows: 3 dates x 11 days = 33. Correct!
print("d=1 new size:", len(pool_idx[1]), "expected 11*11=121 (Jan 1 exists every year)")
print("d=1 new dates:", [date_list[k] for k in pool_idx[1]][:3], [date_list[k] for k in pool_idx[1]][-3:])

# old approach for d=1: doy in [1,6] (lo clipped to 1) -> Jan 1-6 each year = 66 dates
# old approach misses Dec 27-31 of 1991 (dates with doy 361-365 in 1991) whose windows reach Jan 1-6
# EXACT spec: d=1 pool = dates within 5 calendar days of baseline Jan 1 dates -> includes Dec 27-31 1991/1995/... and Jan 1-6 1992-2003
print("old d=1 size:", len(win_old[1]))
print("new d=1 includes 1991-12-27..31:", any(date_list[k] < date(1992,1,1) for k in pool_idx[1]))
print("new d=1 includes 2003-01-01..05:", any(date_list[k] > date(2002,12,31) for k in pool_idx[1]))

# Key check: does 29 Feb belong to windows of its calendar neighbours?
# d=59 (28 Feb): baseline 28 Feb dates +/- 5 calendar days -> includes 29 Feb (calendar neighbour)
print("d=59 new includes Feb 29?", any(date_list[k].month==2 and date_list[k].day==29 for k in pool_idx[59]))
# d=61 (1 Mar): baseline 1 Mar dates +/- 5 calendar -> includes 29 Feb (b-5 for 1 Mar non-leap? 1 Mar - 5 days = 25 Feb non-leap; 1 Mar - 5 days in leap year (e.g., 2000-03-01 - 5 = 2000-02-25)... 
# hmm: 2000-03-01 minus 5 days = 2000-02-25. For 29 Feb to be in window of 1 Mar, need 1 Mar - 5 <= 29 Feb <= 1 Mar + 5 -> 1 Mar - 5 days: in non-leap 1993, 1 Mar - 5 = 24 Feb; in leap, 1 Mar - 5 = 25 Feb. Either way 29 Feb (only in leap years) IS within [24/25 Feb, 6 Mar]. So yes.
print("d=61 new includes Feb 29?", any(date_list[k].month==2 and date_list[k].day==29 for k in pool_idx[61]))
# d=60: no pool (skipped)
print("d=60 in pools:", 60 in pool_idx)
