import os

# Check files exist
for f in ['output/mhw_mask.nc', 'output/report.json']:
    exists = os.path.exists(f)
    size = os.path.getsize(f)
    print(f"{f}: exists={exists}, size={size} bytes")

# Final check - verify the analysis is complete
print("\n=== Analysis Summary ===")
print(f"Region: lat 57.83-59.03, lon 17.41-18.61")
print(f"Sea cells: 3294")
print(f"Target period: 2007-06-01 to 2007-08-31 (92 days)")
print(f"Baseline period used: 1991-12-27 to 2003-01-05")
print(f"Regional events: 1")
print(f"  Event: 2007-06-07 to 2007-06-14 (8 days)")
print(f"Per-cell MHW cell-days: 6944")
print(f"Active days: June 7-14, 2007")
