import json, os
import xarray as xr
ds2 = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print("time encoding:", ds2['time'].encoding.get('units'), "| dtype:", ds2['time'].encoding.get('dtype'))
print("time (decoded):", ds2['time'].values[0], "->", ds2['time'].values[-1])
print("lat:", float(ds2['lat'][0]), float(ds2['lat'][-1]), "| lon:", float(ds2['lon'][0]), float(ds2['lon'][-1]))
rep = json.load(open('/work/output/report.json'))
print("report:", json.dumps(rep))
print("output files:", sorted(os.listdir('/work/output')))
import numpy as np
print("mhw dtype:", ds2['mhw'].dtype, "| values:", np.unique(ds2['mhw'].values), "| sum:", int(ds2['mhw'].sum()))
