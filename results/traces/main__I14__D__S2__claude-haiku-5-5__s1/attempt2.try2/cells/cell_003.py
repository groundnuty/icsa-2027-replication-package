
import xarray as xr, numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
v=ds.analysed_sst
print(v.attrs, v.encoding.get('scale_factor'), v.encoding.get('dtype'))
la=ds.latitude.values; lo=ds.longitude.values
m_la=(la>=56.13-1e-6)&(la<=57.33+1e-6); m_lo=(lo>=17.71-1e-6)&(lo<=18.91+1e-6)
print(la[m_la][[0,-1]], m_la.sum(), lo[m_lo][[0,-1]], m_lo.sum())
