import concurrent.futures as cf, pandas as pd, os
os.makedirs('/tmp/w',exist_ok=True)
dates=[re.search(r'sst_(\d{8})\.nc',f).group(1) for f in files]
dt=pd.to_datetime(dates)
print(dt.min(), dt.max(), len(dt), dt.is_unique, pd.date_range(dt.min(), dt.max()).size)
# coords from first file
lat=ds.latitude.values.astype(float); lon=ds.longitude.values.astype(float)
la=np.where((lat>=54.45-1e-6)&(lat<=55.65+1e-6))[0]; lo=np.where((lon>=16.05-1e-6)&(lon<=17.25+1e-6))[0]
print(len(la), len(lo), lat[la[0]], lat[la[-1]], lon[lo[0]], lon[lo[-1]])
def load(i):
    with fs.open(files[i],'rb') as f:
        d=xarray.open_dataset(f, engine='h5netcdf').load()
    assert np.allclose(d.latitude.values, lat) and np.allclose(d.longitude.values, lon)
    return d.analysed_sst.values[0][np.ix_(la,lo)]
t=time.time()
with cf.ThreadPoolExecutor(16) as ex:
    arr=np.stack(list(ex.map(load, range(len(files)))))
print(time.time()-t, arr.shape)
order=np.argsort(dt.values)
np.savez('/tmp/w/sub.npz', sst=arr[order], dates=dt.values[order].astype('datetime64[D]'), lat=lat[la], lon=lon[lo])
