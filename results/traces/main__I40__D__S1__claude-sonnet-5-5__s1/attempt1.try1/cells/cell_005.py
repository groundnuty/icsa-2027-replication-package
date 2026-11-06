import fsspec,re,os
import pandas as pd, xarray as xr
fs=fsspec.filesystem('onedata')
R='icsa2027_data_20261101T090944Z/s1z'
print([fs.exists(R+f'/sst_{d}.nc') for d in ['19920101','20021231','20030105','19911227','20090831']])
fl2=fs.find(R);print(len(fl2))