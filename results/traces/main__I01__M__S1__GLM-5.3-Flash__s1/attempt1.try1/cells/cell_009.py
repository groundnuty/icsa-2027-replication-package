script = r'''
import numpy as np, h5py, os, datetime as dt, json, time

DATA='/data/icsa2027_data_20261101T090944Z/s1z'
CACHE='/work/cache'
os.makedirs(CACHE, exist_ok=True)
Y0,Y1,X0,X1 = 32,92,284,344  # lat 54.14..55.32, lon 14.68..15.86

def daterange(a,b):
    d=a
    while d<=b:
        yield d
        d+=dt.timedelta(days=1)

def fname(d): return f'{DATA}/sst_{d:%Y%m%d}.nc'

def load_span(d1,d2,tag):
    path=f'{CACHE}/raw_{tag}.npy'
    dates=list(daterange(d1,d2))
    if os.path.exists(path):
        return np.load(path), dates
    arr=np.empty((len(dates),60,60),dtype=np.float64)
    t0=time.time()
    for i,d in enumerate(dates):
        with h5py.File(fname(d),'r') as f:
            arr[i]=f['analysed_sst'][0,Y0:Y1,X0:X1].astype(np.float64)
        if i%400==0: print(tag,i,f'{time.time()-t0:.0f}s',flush=True)
    np.save(path,arr)
    print(tag,'saved',arr.shape,f'{time.time()-t0:.0f}s',flush=True)
    return arr,dates

# ---- load raw data (spans; note DOY windows span one day into 1991 and 2003) ----
raw_91, dates_91 = load_span(dt.date(1991,12,27),dt.date(1991,12,31),'b1991')
raw, dates = load_span(dt.date(1992,1,1),dt.date(2002,12,31),'bmain')
raw_03, dates_03 = load_span(dt.date(2003,1,1),dt.date(2003,1,5),'b2003')
raw_t, dates_t = load_span(dt.date(2008,6,1),dt.date(2008,8,31),'target')
print('raw loaded', raw.shape, raw_t.shape)

np.save(f'{CACHE}/raw_b1991.npy',raw_91); np.save(f'{CACHE}/raw_bmain.npy',raw); np.save(f'{CACHE}/raw_b2003.npy',raw_03); np.save(f'{CACHE}/raw_target.npy',raw_t)
print('DONE_STAGE1')
'''
open('/work/stage1.py','w').write(script)
import subprocess
r = subprocess.run(['python','/work/stage1.py'],capture_output=True,text=True)
print(r.stdout[-3000:])
print(r.stderr[-3000:])
