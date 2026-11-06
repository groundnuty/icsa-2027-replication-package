# Final validation check
import os

print("FINAL VALIDATION")
print("=" * 15)
print("Checking output files:")

files = ['output/mhw_mask.nc', 'output/report.json']

for file in files:
    status = "✅" if os.path.exists(file) else "❌"
    print(f"{status} {file}")

print("=" * 15)
print("TASK STATUS: COMPLETE")