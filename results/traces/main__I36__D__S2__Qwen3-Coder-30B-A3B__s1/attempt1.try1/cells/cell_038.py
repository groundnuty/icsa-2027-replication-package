# Final check
import os

print("🏁 FINAL CHECK")
print("=" * 15)
files = ['output/mhw_mask.nc', 'output/report.json']

all_good = True
for file in files:
    exists = os.path.exists(file)
    print(f"{'✓' if exists else '✗'} {file}")
    if not exists:
        all_good = False

print("=" * 15)
if all_good:
    print("SUCCESS: All files generated")
    print("Task completed as requested")
else:
    print("FAILURE: Missing files")