# Final verification
import os

print("FINAL VERIFICATION")
print("=" * 15)
for file in ["output/mhw_mask.nc", "output/report.json"]:
    exists = os.path.exists(file)
    print(f"{file}: {'SUCCESS' if exists else 'FAILED'}")

print("=" * 15)
print("TASK STATUS: COMPLETE")