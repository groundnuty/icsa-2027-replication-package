
import os
import numpy as np
import xarray as xr
import json

# Check output files exist
print("Output files:")
print(f"  mhw_mask.nc: {'EXISTS' if os.path.exists('output/mhw_mask.nc') else 'MISSING'}")
print(f"  report.json: {'EXISTS' if os.path.exists('output/report.json') else 'MISSING'}")

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"\nmhw_mask.nc:")
print(f"  Dimensions: {dict(ds.sizes)}")
print(f"  Variables: {list(ds.data_vars)}")
print(f"  mhw dtype: {ds.mhw.dtype}")
print(f"  mhw shape: {ds.mhw.shape}")
print(f"  mhw min/max: {ds.mhw.values.min()}/{ds.mhw.values.max()}")
print(f"  mhw sum: {ds.mhw.values.sum()}")
print(f"  Time range: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"  Lat range: {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"  Lon range: {ds.lon.values[0]} to {ds.lon.values[-1]}")

# Verify land cells are 0
# Load target data to check sea cells
target_data = np.load('/tmp/target_data.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
mhw = ds.mhw.values

# For each target day, check land cells have mhw=0
land_cells = ~sea_cells
for t in range(mhw.shape[0]):
    if mhw[t, land_cells].any():
        print(f"ERROR: Land cells have mhw=1 on day {t}")
        break
else:
    print(f"  All land cells have mhw=0 ✓")

# Verify sea cells match
for t in range(mhw.shape[0]):
    # mhw should only be 1 for sea cells
    pass  # Already checked above

# Check that mhw is 1 where cell is in per-cell MHW
cell_mhw = np.load('/tmp/cell_mhw.npy')
match = (mhw == cell_mhw.astype(np.uint8)).all()
print(f"  mhw matches cell_mhw: {match}")

ds.close()

# Verify report.json
with open('output/report.json') as f:
    report = json.load(f)
print(f"\nreport.json:")
print(f"  region: {report['region']}")
print(f"  baseline_analysed: {report['baseline_analysed']}")
print(f"  target_analysed: {report['target_analysed']}")
print(f"  events: {report['events']}")
print(f"  complete: {report['complete']}")
print(f"  caveats: {report['caveats']}")

# Verify events consistency with mhw_mask
active_days = cell_mhw.any(axis=(1,2))
with open('/tmp/target_dates.txt') as f:
    target_dates_str = [line.strip() for line in f]
from datetime import date
target_dates = [date.fromisoformat(s) for s in target_dates_str]

for ev in report['events']:
    onset = date.fromisoformat(ev['onset'])
    end = date.fromisoformat(ev['end'])
    # Check that onset and end are valid target dates
    assert onset in target_dates, f"Onset {onset} not in target dates"
    assert end in target_dates, f"End {end} not in target dates"
    # Check that all days between onset and end are active
    for d in target_dates:
        if onset <= d <= end:
            idx = target_dates.index(d)
            assert active_days[idx], f"Day {d} is not active but is within event"
    # Check that days before onset and after end are not active (for the maximal run)
    idx_onset = target_dates.index(onset)
    idx_end = target_dates.index(end)
    # The days just before onset and just after end should be inactive
    if idx_onset > 0:
        assert not active_days[idx_onset - 1], f"Day before onset is active"
    if idx_end < len(target_dates) - 1:
        assert not active_days[idx_end + 1], f"Day after end is active"

print(f"\nAll verification checks passed!")
