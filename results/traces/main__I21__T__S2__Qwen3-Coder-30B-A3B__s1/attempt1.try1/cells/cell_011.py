# Verify final files exist
import os
print("Files created:")
print("-" * 30)
if os.path.exists('output/mhw_mask.nc'):
    print("✓ output/mhw_mask.nc")
else:
    print("✗ output/mhw_mask.nc")

if os.path.exists('output/report.json'):
    print("✓ output/report.json")
else:
    print("✗ output/report.json")

print("\nAnalysis complete!")