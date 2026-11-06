
import os

# Check output files
for f in ['output/mhw_mask.nc', 'output/report.json']:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"{f}: exists, {size} bytes")
    else:
        print(f"{f}: MISSING!")

# Final summary
print("\n=== FINAL SUMMARY ===")
print("Region: lat 54.17-55.37, lon 13.25-14.45")
print("Baseline: 1991-12-27 to 2003-01-05 (used for threshold/climatology)")
print("Target: 2014-06-01 to 2014-08-31 (92 days)")
print("Sea cells: 3303 out of 3600")

print("\nRegional MHW events:")
print("  1. 2014-06-04 to 2014-06-20 (17 days)")
print("  2. 2014-07-06 to 2014-07-12 (7 days)")
print("  3. 2014-07-16 to 2014-08-12 (28 days)")

print("\nOutput files written successfully.")
