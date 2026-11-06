# Final check
import os

print("FINAL CHECK")
print("=" * 15)
files = ["output/mhw_mask.nc", "output/report.json"]

all_good = True
for file in files:
    exists = os.path.exists(file)
    status = "OK" if exists else "MISSING"
    print(f"{file:<25} {status}")
    if not exists:
        all_good = False

print("=" * 15)
print(f"RESULT: {'SUCCESS' if all_good else 'FAILURE'}")