import xarray as xr, json
d=xr.open_dataset('/work/output/mhw_mask.nc') if False else None
import subprocess
print(subprocess.run("cd /work && python -c \"import xarray as xr;d=xr.open_dataset('output/mhw_mask.nc');print(d);print(d.mhw.dtype)\" && cat output/report.json",shell=True,capture_output=True,text=True).stdout[-3000:])