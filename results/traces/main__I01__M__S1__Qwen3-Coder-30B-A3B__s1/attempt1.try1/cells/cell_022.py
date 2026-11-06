# One final check
import os

files = ["output/mhw_mask.nc", "output/report.json"]
all_present = all(os.path.exists(f) for f in files)

print("FINAL CHECK")
print("-" * 10)
for file in files:
    print(f"{file}: {'PASS' if os.path.exists(file) else 'FAIL'}")

print("-" * 10)
print(f"Overall: {'SUCCESS' if all_present else 'FAILURE'}")
print("TASK COMPLETED")