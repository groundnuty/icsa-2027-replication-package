import time
print(ds.analysed_sst.attrs)
lat=ds.latitude.values; lon=ds.longitude.values
li=np.where((lat>=54.39)&(lat<=55.59))[0]; lo=np.where((lon>=18.25)&(lon<=19.45))[0]
print(li.min(),li.max(),len(li), lo.min(),lo.max(),len(lo), lat[li][[0,-1]], lon[lo][[0,-1]])
a=ds.analysed_sst.values[0,li.min():li.max()+1,lo.min():lo.max()+1]
print(np.nanmin(a),np.nanmax(a), np.isnan(a).mean())
t0=time.time(); x=xr.open_dataset(f"{D}/sst_19950601.nc",engine="h5netcdf").analysed_sst.isel(latitude=slice(li.min(),li.max()+1),longitude=slice(lo.min(),lo.max()+1)).values; print(time.time()-t0)