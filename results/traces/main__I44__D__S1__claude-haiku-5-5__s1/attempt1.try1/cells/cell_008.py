import fsspec, os, time, numpy as np, xarray as xr
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/t',exist_ok=True)
t=time.time(); fs.get(f'{base}/sst_20040601.nc','/work/t/a.nc'); print('dl',time.time()-t)
ds=xr.open_dataset('/work/t/a.nc',engine='h5netcdf')
print(ds.analysed_sst.attrs, ds.analysed_sst.encoding.get('dtype'))
lat=ds.latitude.values; lon=ds.longitude.values
ri=np.where((lat>=63.31)&(lat<=64.51))[0]; ci=np.where((lon>=21.31)&(lon<=22.51))[0]
print(len(ri),len(ci), lat[ri[[0,-1]]], lon[ci[[0,-1]]])
print(os.popen('df -h /work | tail -1').read())
print(float(np.isfinite(ds.analysed_sst.values[0,ri][:,ci]).mean()))