import xarray as xr, numpy as np, os
P='/data/icsa2027_data_20261101T090944Z/s1z/'
d=xr.open_dataset(P+'sst_19820101.nc',engine='h5netcdf')
v=d.analysed_sst
print(v.attrs); print(v.encoding)
a=v.values[0]; print(np.nanmin(a),np.nanmax(a),np.isnan(a).sum(), a.shape)
lat=d.latitude.values; lon=d.longitude.values
print(np.unique(np.round(np.diff(lat),6)), np.unique(np.round(np.diff(lon),6)))