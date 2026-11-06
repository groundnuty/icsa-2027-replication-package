# Verify that output files were created
import os
print("Output files created:")
print("-" * 30)
if os.path.exists('output/mhw_mask.nc'):
    print("✓ mhw_mask.nc - MHW mask NetCDF file")
else:
    print("✗ mhw_mask.nc - Missing")

if os.path.exists('output/report.json'):
    print("✓ report.json - Analysis report")
else:
    print("✗ report.json - Missing")

print("\nAnalysis complete!")