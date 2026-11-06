import time, numpy as np, xarray as xr
print(ds.analysed_sst.attrs)
lat=ds.latitude.values; lon=ds.longitude.values
ri=np.where((lat>=63.31)&(lat<=64.51))[0]; ci=np.where((lon>=21.31)&(lon<=22.51))[0]
print(len(ri),len(ci), lat[ri[[0,-1]]], lon[ci[[0,-1]]])
t=time.time(); fs.get(f'{base}/sst_20040602.nc','/work/t/b.nc'); print('dl',time.time()-t)
print(os.popen('df -h /work | tail -1').read())