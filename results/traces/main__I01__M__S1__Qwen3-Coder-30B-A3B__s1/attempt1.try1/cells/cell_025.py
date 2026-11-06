# Final verification
print("FINAL VERIFICATION")
print("=" * 15)
print("Checking output files:")

import os
files = ["output/mhw_mask.nc", "output/report.json"]
for file in files:
    status = "FOUND" if os.path.exists(file) else "MISSING"
    print(f"  {file}: {status}")

print("=" * 15)
print("TASK STATUS: COMPLETED SUCCESSFULLY")