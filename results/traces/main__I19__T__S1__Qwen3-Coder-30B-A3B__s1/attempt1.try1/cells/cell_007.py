# Final verification that both output files exist
import os

print("Checking output files:")
if os.path.exists('output/mhw_mask.nc'):
    print("✓ mhw_mask.nc exists")
else:
    print("✗ mhw_mask.nc missing")

if os.path.exists('output/report.json'):
    print("✓ report.json exists")
else:
    print("✗ report.json missing")

print("\nSolution complete!")