import numpy as np, json, os, warnings, xarray as xr
warnings.filterwarnings('ignore')
R=np.load('/tmp/results2.npz'); mem=R['mem']; sea_cols=R['sea_cols']; events=R['events']
v=xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mv=v['mhw'].values
print("dims:", dict(v.sizes), "| dtype:", mv.dtype, "| vals:", np.unique(mv))
flat=mv.reshape(mv.shape[0],-1)
land=np.setdiff1d(np.arange(3600), sea_cols)
print("mask equals mem on sea cols:", bool((flat[:,sea_cols]==mem.astype(np.uint8)).all()),
      "| land all zero:", bool(flat[:,land].max()==0))
print("time:", str(v['time'].values[0])[:10], "..", str(v['time'].values[-1])[:10], "n=", v['time'].size)
print("lat:", float(v['lat'][0]), "..", float(v['lat'][-1]), "| lon:", float(v['lon'][0]), "..", float(v['lon'][-1]))
print("active days from file:", int((flat.max(axis=1)>0).sum()))
r=json.load(open('output/report.json'))
print("report keys:", list(r.keys()))
print(json.dumps(r, indent=1))
print("mhw attrs:", v['mhw'].attrs)
print("both files exist:", os.path.exists('output/mhw_mask.nc'), os.path.exists('output/report.json'))
