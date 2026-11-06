# Final verification that both files were created
import os

print("Checking output files:")
if os.path.exists("output/mhw_mask.nc"):
    print("✓ mhw_mask.nc exists")
else:
    print("✗ mhw_mask.nc missing")

if os.path.exists("output/report.json"):
    print("✓ report.json exists")
else:
    print("✗ report.json missing")

print("\nOutput directory contents:")
print(os.listdir("output"))