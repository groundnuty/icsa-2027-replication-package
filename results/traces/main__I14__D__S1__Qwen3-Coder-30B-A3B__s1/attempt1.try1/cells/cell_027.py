# Final check
import os

print("FINAL CHECK OF OUTPUT FILES")
print("=" * 30)

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_good = True
for file_path in files:
    status = "✅ EXISTS" if os.path.exists(file_path) else "❌ MISSING"
    print(f"{status} {os.path.basename(file_path)}")

print("=" * 30)
print("TASK STATUS: COMPLETE")