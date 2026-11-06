import xarray as xr, numpy as np, json
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
m = ds['mhw'].values
si = np.load('/work/data/sea_idx.npy')
sea = np.zeros((60,60), bool); sea[si//60, si%60] = True
ok = True
for r in range(m.shape[1]):
    for c in range(m.shape[2]):
        col = m[:, r, c]
        if col.any():
            idx = np.flatnonzero(col)
            if not (idx.min() >= 31 and idx.max() <= 36 and len(idx) == idx.max()-idx.min()+1):
                ok = False
print("all MHW blocks contiguous within 07-02..07-07:", ok)
# sea cells with MHW should be exactly 926
print("cells with MHW:", int((m.sum(axis=0) > 0).sum()))
ds.close()

rep = json.load(open('output/report.json'))
assert set(rep.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert rep["region"] == {"lat_min":56.13,"lat_max":57.33,"lon_min":17.71,"lon_max":18.91}
assert rep["baseline_analysed"] == {"start":"1992-01-01","end":"2002-12-31"}
assert rep["target_analysed"] == {"start":"2015-06-01","end":"2015-08-31"}
assert rep["events"] == [{"onset":"2015-07-02","end":"2015-07-07"}]
assert rep["complete"] is True
assert isinstance(rep["caveats"], str)
print("report.json OK")
print(json.dumps(rep, indent=1))
import os
print(os.path.abspath('output/mhw_mask.nc'), os.path.getsize('output/mhw_mask.nc'))
print(os.path.abspath('output/report.json'), os.path.getsize('output/report.json'))