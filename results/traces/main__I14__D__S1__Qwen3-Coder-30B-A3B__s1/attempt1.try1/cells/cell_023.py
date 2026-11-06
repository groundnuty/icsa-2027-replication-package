# One final check
import os

print("FINAL CHECK")
print("-" * 15)
files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_good = True
for f in files:
    exists = os.path.exists(f)
    print(f"{'✓' if exists else '✗'} {os.path.basename(f)}")
    if not exists:
        all_good = False

print("-" * 15)
print("RESULT: " + ("SUCCESS" if all_good else "FAILURE"))