
import os, datetime as dt
print("marker exists:", os.path.exists("/work/marker.txt"), open("/work/marker.txt").read() if os.path.exists("/work/marker.txt") else None)
# build required date lists
def daterange(a, b):
    d = a
    out = []
    while d <= b:
        out.append(d); d += dt.timedelta(days=1)
    return out
baseline_win = daterange(dt.date(1991,12,27), dt.date(2003,1,5))   # windows for pools
target = daterange(dt.date(2021,6,1), dt.date(2021,8,31))
print("baseline window days:", len(baseline_win), baseline_win[0], baseline_win[-1])
print("target days:", len(target))
# verify leap-year doy mapping
leap = dt.date(2000,1,1)
def doy(d): return (dt.date(2000,d.month,d.day) - leap).days + 1
print("doy 2021-06-01:", doy(dt.date(2021,6,1)), "doy 2021-08-31:", doy(dt.date(2021,8,31)), "doy 2001-03-01:", doy(dt.date(2001,3,1)))
all_days = sorted(set(baseline_win) | set(target))
print("total files needed:", len(all_days))
import pickle
with open("/work/dates.pkl","wb") as f:
    pickle.dump({"baseline_win":[d.isoformat() for d in baseline_win], "target":[d.isoformat() for d in target]}, f)
print("saved date lists")
