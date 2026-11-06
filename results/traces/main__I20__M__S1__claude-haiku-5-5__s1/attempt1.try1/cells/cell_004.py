import xarray as xr, numpy as np
D="/data/icsa2027_data_20261101T090944Z/s1z"
ds=xr.open_dataset(D+"/sst_19820101.nc",engine="h5netcdf")
print(ds.attrs['comment'])
lat=ds.latitude.values.astype(float); lon=ds.longitude.values.astype(float)
li=np.where((lat>=57.33-1e-6)&(lat<=58.53+1e-6))[0]; lj=np.where((lon>=9.03-1e-6)&(lon<=10.23+1e-6))[0]
print(len(li),len(lj), lat[li[0]],lat[li[-1]],lon[lj[0]],lon[lj[-1]])
print(ds.analysed_sst.encoding)