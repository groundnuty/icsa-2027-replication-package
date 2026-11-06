# Final status check
import os

print("FINAL STATUS CHECK")
print("=" * 20)
files_to_check = ["output/mhw_mask.nc", "output/report.json"]

all_good = True
for file in files_to_check:
    exists = os.path.exists(file)
    print(f"{file}: {'✓' if exists else '✗'} {'FOUND' if exists else 'MISSING'}")
    if not exists:
        all_good = False

print("=" * 20)
print(f"OVERALL: {'SUCCESS' if all_good else 'FAILURE'}")