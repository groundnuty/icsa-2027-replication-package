
import os, datetime as dt, pickle, numpy as np
os.makedirs('/work/mhw', exist_ok=True)

code = '''
import os, io, datetime as dt, pickle, time
import numpy as np
import fsspec, xarray

BASE = '/icsa2027_data_20261101T090944Z/s1z'
LAT_SLICE = (260, 320)   # grid rows 58.70 .. 59.88
LON_SLICE = (485, 545)   # grid cols 18.70 .. 19.88
NCELL = 3600

def all_dates():
    ext = [dt.date(1991,12,27) + dt.timedelta(days=k) for k in range((dt.date(2003,1,5)-dt.date(1991,12,27)).days+1)]
    tgt = [dt.date(2010,6,1) + dt.timedelta(days=k) for k in range((dt.date(2010,8,31)-dt.date(2010,6,1)).days+1)]
    return ext, tgt

def datekey(d): return f"{d.year:04d}{d.month:02d}{d.day:02d}"

def fetch_one(fs, d):
    path = f"{BASE}/sst_{datekey(d)}.nc"
    f = fs.open(path, "rb")
    ds = xarray.open_dataset(f, engine="h5netcdf")
    a = ds["analysed_sst"].values[0, LAT_SLICE[0]:LAT_SLICE[1], LON_SLICE[0]:LON_SLICE[1]].astype(np.float32)
    ds.close(); f.close()
    return a.ravel(order="C")

def load_state():
    p = "/work/mhw/state.npz"
    if os.path.exists(p):
        z = np.load(p)
        return z["ext"], z["tgt"], set(z["done"].tolist())
    ext, tgt = all_dates()
    return (np.full((len(ext), NCELL), np.nan, np.float32),
            np.full((len(tgt), NCELL), np.nan, np.float32),
            set())

def save_state(ext, tgt, done):
    np.savez("/work/mhw/state.npz", ext=ext, tgt=tgt, done=np.array(sorted(done), dtype="U8"))
'''
with open('/work/mhw/common.py','w') as fh:
    fh.write(code)

# quick sanity: run the loader
import sys; sys.path.insert(0,'/work/mhw')
import common
ext, tgt, done = common.load_state()
print(ext.shape, tgt.shape, len(done))
print(ext[0], ext[-1], '->', tgt[0], tgt[-1])
print('ext days:', len(ext), 'tgt days:', len(tgt))
