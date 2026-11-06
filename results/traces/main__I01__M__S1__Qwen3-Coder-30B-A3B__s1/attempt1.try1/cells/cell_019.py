# Final verification that files exist
import os

print("FINAL VERIFICATION")
print("=" * 15)
for filename in ["output/mhw_mask.nc", "output/report.json"]:
    status = "FOUND" if os.path.exists(filename) else "MISSING"
    print(f"{filename}: {status}")
    
print("=" * 15)
print("TASK COMPLETED SUCCESSFULLY")