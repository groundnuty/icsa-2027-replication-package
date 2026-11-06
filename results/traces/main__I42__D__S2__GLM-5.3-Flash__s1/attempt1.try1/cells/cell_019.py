import os, json, numpy as np, xarray as xr
print("cwd:", os.getcwd())
print("output/ contents:", os.listdir('output'))
for fn in ['output/mhw_mask.nc', 'output/mhw_report.json']:
    p = os.path.abspath(fn); print(fn, "->", p, os.path.getsize(p), "bytes")

# independent re-verification of the mask against per_cell.npy
z = np.load('/work/final.npz'); per_cell = z['per_cell']
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds['mhw'].values
print("mask == per_cell:", bool(np.array_equal(mhw, per_cell.astype(np.uint8))))
print("mask dtype:", mhw.dtype, "| unique values:", np.unique(mhw), "| sum:", int(mhw.sum()))
rep = json.load(open('output/mhw_report.json'))
print("report keys:", list(rep.keys()))
print("events:", rep['events'])
# confirm event days in mask match
t = ds['time'].values
aug = [i for i,d in enumerate(t) if str(d)[:10] >= '2012-08-15' and str(d)[:10] <= '2012-08-19']
print("mask days with mhw>0:", [str(t[i])[:10] for i in range(len(t)) if mhw[i].sum() > 0])
print("cells in mhw on Aug15:", int(mhw[aug[0]].sum()), "| Aug19:", int(mhw[aug[-1]].sum()))
ds.close()
