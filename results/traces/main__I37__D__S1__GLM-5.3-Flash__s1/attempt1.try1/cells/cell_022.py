import os, glob, datetime as dt
import h5py, numpy as np

files = sorted(glob.glob('/work/data/sst_*.nc'))
print("files:", len(files))

def read_time_h5(path):
    with h5py.File(path, 'r') as f:
        return f['time'][:][0]

tvals = []
bad = []
for f in files:
    try:
        tvals.append(read_time_h5(f))
    except Exception as e:
        bad.append((os.path.basename(f), str(e)[:80]))
print("time-read failures:", len(bad), bad[:5])
tvals = np.array(tvals, dtype='datetime64[ns]')
# expect contiguous daily from 1991-12-27 to 2003-01-05, then 2012-06-01..2012-08-31
expected = np.concatenate([
    np.arange(np.datetime64('1991-12-27'), np.datetime64('2003-01-06'), dtype='datetime64[D]').astype('datetime64[ns]'),
    np.arange(np.datetime64('2012-06-01'), np.datetime64('2012-09-01'), dtype='datetime64[D]').astype('datetime64[ns]'),
]).astype('datetime64[ns]')
print("expected:", len(expected), "got:", len(tvals))
print("sorted?", (tvals == np.sort(tvals)).all())
print("match:", (tvals == expected).all())
if not (tvals == expected).all():
    idx = np.where(tvals != expected)[0]
    print("mismatch idx:", idx[:10], tvals[idx[:10]], expected[idx[:10]])
