
import os, shutil, json, subprocess
os.makedirs('output',exist_ok=True)
shutil.copy('/tmp/w/out/mhw_mask.nc','output/mhw_mask.nc'); shutil.copy('/tmp/w/out/report.json','output/report.json')
print(os.getcwd(), os.listdir('output'))
print(json.load(open('output/report.json'))['events'])
import xarray as xr
print(xr.open_dataset('output/mhw_mask.nc').mhw.dims, xr.open_dataset('output/mhw_mask.nc').mhw.dtype)
