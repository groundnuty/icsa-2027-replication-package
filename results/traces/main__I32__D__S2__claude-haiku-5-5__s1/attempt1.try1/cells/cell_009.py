
import xarray as xr, json
o=xr.open_dataset('/work/output/mhw_mask.nc') if False else None
import subprocess
print(subprocess.run(['python','-c',"import xarray as xr;o=xr.open_dataset('/work/output/mhw_mask.nc');print(o);print(o.mhw.dtype)"],capture_output=True,text=True,cwd='/work').stdout)
print(open('/work/output/report.json').read()[:1500])
