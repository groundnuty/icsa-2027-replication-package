# Final status check
import os

print("STATUS CHECK")
print("-" * 15)
files = ["output/mhw_mask.nc", "output/report.json"]
all_good = True

for file in files:
    status = "OK" if os.path.exists(file) else "MISSING"
    print(f"{file:<25} {status}")
    if not os.path.exists(file):
        all_good = False

print("-" * 15)
print(f"OVERALL: {'SUCCESS' if all_good else 'FAILURE'}")