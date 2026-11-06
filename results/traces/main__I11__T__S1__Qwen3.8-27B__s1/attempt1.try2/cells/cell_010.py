
import fsspec, time, pickle
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base='/icsa2027_data_20261101T090944Z/s1z/'
dates = pickle.load(open("/work/dates.pkl","rb"))
all_days = sorted(set(dates["baseline_win"]) | set(dates["target"]))
def check(s):
    p = base + "sst_" + s.replace("-","") + ".nc"
    try:
        fs.head(p)
        return (s, True)
    except Exception as e:
        return (s, False)
t0=time.time()
missing = []
with ThreadPoolExecutor(max_workers=24) as ex:
    for s, ok in ex.map(check, all_days):
        if not ok: missing.append(s)
print("checked", len(all_days), "files in", round(time.time()-t0,1), "s; missing:", missing)
pickle.dump({"missing": missing}, open("/work/missing.pkl","wb"))
