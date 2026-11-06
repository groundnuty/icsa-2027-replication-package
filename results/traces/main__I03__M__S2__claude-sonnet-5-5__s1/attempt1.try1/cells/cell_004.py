
import xarray as xr, numpy as np, pandas as pd
p="/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
d=xr.open_dataset(p,engine="h5netcdf")
la=d.latitude.values;lo=d.longitude.values
iy=np.where((la>=54.17-1e-4)&(la<=55.37+1e-4))[0];ix=np.where((lo>=13.25-1e-4)&(lo<=14.45+1e-4))[0]
print(la[iy][[0,-1]],lo[ix][[0,-1]],len(iy),len(ix))
s=d.analysed_sst.isel(latitude=slice(iy[0],iy[-1]+1),longitude=slice(ix[0],ix[-1]+1)).load()
print(s.dtype,float(s.max()),float(s.min()),len(s.time))
s.to_netcdf("/tmp/s.nc")
