
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=57.85-1e-6)&(lat<=59.05+1e-6))[0]; lo=np.where((lon>=21.01-1e-6)&(lon<=22.21+1e-6))[0]
print(len(la),len(lo),lat[la[0]],lat[la[-1]],lon[lo[0]],lon[lo[-1]])
sub=ds.analysed_sst.isel(latitude=la,longitude=lo)
import pandas as pd
base=sub.sel(time=slice('1991-12-27','2003-01-05')).load()
tgt=sub.sel(time=slice('2013-06-01','2013-08-31')).load()
print(base.shape,tgt.shape, np.isnan(base.values).mean(), np.isnan(tgt.values).mean())
