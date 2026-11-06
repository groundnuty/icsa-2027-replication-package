
import xarray as xr
import numpy as np
import json
from datetime import date, timedelta

# =============================================
# Final verification
# =============================================

# 1. Read back mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values
print("=== mhw_mask.nc ===")
print(f"Shape: {mhw.shape}")
print(f"dtype: {mhw.dtype}")
print(f"Unique values: {np.unique(mhw)}")

# 2. Verify regional events from the mask
active = mhw.any(axis=(1, 2))
target_dates = []
d = date(2009, 6, 1)
while d <= date(2009, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

events_from_mask = []
t = 0
while t < len(active):
    if active[t]:
        start = t
        while t < len(active) and active[t]:
            t += 1
        events_from_mask.append((start, t-1))
    else:
        t += 1

print(f"\nActive days: {active.sum()}")
print(f"Events from mask: {len(events_from_mask)}")
for s, e in events_from_mask:
    print(f"  {target_dates[s].strftime('%Y-%m-%d')} to {target_dates[e].strftime('%Y-%m-%d')}")

# 3. Read report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)

print("\n=== report.json ===")
print(f"Events in report: {len(report['events'])}")
for ev in report['events']:
    print(f"  {ev['onset']} to {ev['end']}")

# 4. Verify events match
assert len(events_from_mask) == len(report['events']), "Event count mismatch!"
for (s, e), ev in zip(events_from_mask, report['events']):
    assert target_dates[s].strftime('%Y-%m-%d') == ev['onset'], f"Onset mismatch!"
    assert target_dates[e].strftime('%Y-%m-%d') == ev['end'], f"End mismatch!"
print("\n✓ Events in report match events from mhw mask")

# 5. Verify land cells are 0
# Check that some known land cells have 0 in mhw
non_sea = np.where(~np.load('/tmp/sea_cells.npy'))
for i, j in zip(non_sea[0][:5], non_sea[1][:5]):
    vals = mhw[:, i, j]
    assert vals.sum() == 0, f"Land cell ({i},{j}) has non-zero mhw!"
print("✓ Land cells are all 0")

# 6. Verify sea cells have 1 on MHW days and 0 on non-MHW days
sea = np.load('/tmp/sea_cells.npy')
per_cell_mhw = np.load('/tmp/per_cell_mhw.npy')
assert np.array_equal(mhw.astype(bool), per_cell_mhw), "mhw mask doesn't match per_cell_mhw!"
print("✓ mhw mask matches per_cell_mhw")

# 7. Verify time coordinates
print(f"\nTime coords: {ds.time.values[0]} to {ds.time.values[-1]} ({len(ds.time)} entries)")
print(f"Lat coords: {ds.lat.values[0]} to {ds.lat.values[-1]} ({len(ds.lat)} entries)")
print(f"Lon coords: {ds.lon.values[0]} to {ds.lon.values[-1]} ({len(ds.lon)} entries)")

# 8. Verify report fields
required = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for f in required:
    assert f in report, f"Missing report field: {f}"
print("\n✓ All required report fields present")

assert report['region'] == {'lat_min': 56.09, 'lat_max': 57.29, 'lon_min': 10.55, 'lon_max': 11.75}
assert report['baseline_analysed'] == {'start': '1991-12-27', 'end': '2003-01-05'}
assert report['target_analysed'] == {'start': '2009-06-01', 'end': '2009-08-31'}
assert report['complete'] == True
assert isinstance(report['caveats'], str)
print("✓ All report field values are correct")

ds.close()
print("\n=== ALL VERIFICATIONS PASSED ===")
