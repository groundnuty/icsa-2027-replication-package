import xarray as xr, numpy as np, json
ds = xr.open_dataset('/work/output/mhw_mask.nc')
print(ds)
m = ds['mhw']
print("dtype:", m.dtype, "dims:", m.dims, "shape:", m.shape)
print("time[0]/[-1]:", ds['time'].values[0], ds['time'].values[-1])
print("lat range:", float(ds['lat'].values[0]), float(ds['lat'].values[-1]), "n=", len(ds['lat']))
print("lon range:", float(ds['lon'].values[0]), float(ds['lon'].values[-1]), "n=", len(ds['lon']))
vals = m.values
print("unique values:", np.unique(vals), "total ones:", int(vals.sum()))
# land cells zero? compare with sea mask
sea = np.load('/work/sea.npy')
land_cols = (~sea).reshape(60,60)
land_days_sum = vals.sum(axis=0)
sub = vals.reshape(92,60,60)
print("land cells ever nonzero:", int(sub[:, land_cols].sum()))
# active days per day and events
active = vals.sum(axis=(1,2)) > 0
import datetime as dt
dates = [dt.date(2009,6,1)+dt.timedelta(days=i) for i in range(92)]
ev = []
i = 0
while i < 92:
    if active[i]:
        j = i
        while j+1 < 92 and active[j+1]: j += 1
        ev.append([dates[i].isoformat(), dates[j].isoformat()]); i = j+1
    else: i += 1
print("recomputed events:", ev)
rep = json.load(open('/work/output/report.json'))
assert rep["events"] == [{"onset": a, "end": b} for a,b in ev], "event mismatch"
print("report events consistent with mask: True")
print(json.dumps(rep, indent=1)[:600])
ds.close()
