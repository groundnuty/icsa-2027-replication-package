import os,glob
fs=sorted(os.listdir('/data/icsa2027_data_20261101T090944Z/s1z'))
print(len(fs),fs[0],fs[-1])
import xarray as xr
d=xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/'+fs[0],engine='h5netcdf')
print(d)
print(set(f[:4] for f in fs), [f for f in fs if not f.startswith('sst_')][:5])