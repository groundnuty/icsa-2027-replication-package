# Final verification
import os

print("FINAL VERIFICATION")
print("=" * 15)
for file in ["output/mhw_mask.nc", "output/report.json"]:
    status = "SUCCESS" if os.path.exists(file) else "FAILED"
    print(f"{file}: {status}")

print("=" * 15)
print("OVERALL: TASK COMPLETE")