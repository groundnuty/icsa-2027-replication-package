import os, json, numpy as np, xarray as xr
print(os.getcwd(), os.path.exists('output/report.json'), os.path.exists('output/mhw_mask.nc'))
print(os.path.abspath('output/mhw_mask.nc'))
ds=xr.open_dataset('output/mhw_mask.nc'); print(ds)
print(json.load(open('output/report.json'))['events'])
