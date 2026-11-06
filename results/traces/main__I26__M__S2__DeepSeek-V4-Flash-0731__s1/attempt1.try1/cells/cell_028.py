
import numpy as np
import xarray as xr
import json

# Check output files
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print(f"Shape: {ds.mhw.shape}")
print(f"dtype: {ds.mhw.dtype}")
print(f"Time range: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"Lat range: {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"Lon range: {ds.lon.values[0]} to {ds.lon.values[-1]}")
print(f"Values: {np.unique(ds.mhw.values)}")
print(f"Sum of mhw: {ds.mhw.values.sum()}")
print()

# Check regional events
mhw = ds.mhw.values
active = mhw.any(axis=(1, 2))
print(f"Active days: {np.where(active)[0]}")
ds.close()

# Check report
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\n=== report.json ===")
print(json.dumps(report, indent=2))

# Verify events match active days
tgt_start = np.datetime64('2007-06-01')
events = report['events']
print("\n=== Event verification ===")
for e in events:
    onset = np.datetime64(e['onset'])
    end = np.datetime64(e['end'])
    onset_idx = (onset - tgt_start).astype('timedelta64[D]').astype(int)
    end_idx = (end - tgt_start).astype('timedelta64[D]').astype(int)
    print(f"Event {e['onset']} to {e['end']}: indices {onset_idx} to {end_idx}")
    # Check that these indices are all active
    assert np.all(active[onset_idx:end_idx+1]), f"Not all days in event are active!"
    # Check that the event is maximal
    if onset_idx > 0:
        assert not active[onset_idx-1], f"Day {onset_idx-1} is active but not in event!"
    if end_idx < len(active)-1:
        assert not active[end_idx+1], f"Day {end_idx+1} is active but not in event!"
print("All events verified as maximal runs of active days.")
