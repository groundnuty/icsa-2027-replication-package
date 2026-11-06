import os, datetime as dt
print("cwd:", os.getcwd())
print("tmp writable:", os.access('/tmp', os.W_OK))
os.makedirs('output', exist_ok=True)
os.makedirs('/tmp/mhw', exist_ok=True)

base = "/data/icsa2027_data_20261101T090944Z/s1z"
ext_start, ext_end = dt.date(1991,12,27), dt.date(2003,1,5)
tgt_start, tgt_end = dt.date(2012,6,1), dt.date(2012,8,31)
def daterange(a, b):
    d, out = a, []
    while d <= b:
        out.append(d); d += dt.timedelta(days=1)
    return out
ext_dates = daterange(ext_start, ext_end)
tgt_dates = daterange(tgt_start, tgt_end)
print("ext days:", len(ext_dates), "tgt days:", len(tgt_dates))
allf = [f"sst_{d.strftime('%Y%m%d')}.nc" for d in ext_dates + tgt_dates]
missing = [f for f in allf if not os.path.exists(os.path.join(base, f))]
print("missing files:", missing[:10], "count:", len(missing))
import pickle
with open('/tmp/mhw/dates.pkl','wb') as fh:
    pickle.dump({'ext':[str(d) for d in ext_dates], 'tgt':[str(d) for d in tgt_dates], 'base':base}, fh)
print("ok")
