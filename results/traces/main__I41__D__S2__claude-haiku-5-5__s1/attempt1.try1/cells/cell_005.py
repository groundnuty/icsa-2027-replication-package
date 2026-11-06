
import xarray as xr, numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
v=ds.analysed_sst
print(v.attrs); print(v.encoding)
lat=ds.latitude.values; lon=ds.longitude.values
m_la=(lat>=61.57-1e-6)&(lat<=62.77+1e-6); m_lo=(lon>=20.17-1e-6)&(lon<=21.37+1e-6)
print(lat[m_la].min(), lat[m_la].max(), m_la.sum())
print(lon[m_lo].min(), lon[m_lo].max(), m_lo.sum())
print(ds.time.values[:3], ds.time.values[-1], len(ds.time))
