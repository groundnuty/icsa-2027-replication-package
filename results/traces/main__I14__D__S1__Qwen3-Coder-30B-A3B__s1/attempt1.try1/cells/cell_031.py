# Final check
print("FINAL TASK STATUS")
print("=" * 20)

import os

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_good = True
for file_path in files:
    exists = os.path.exists(file_path)
    status = "✅" if exists else "❌"
    print(f"{status} {os.path.basename(file_path)}")
    if not exists:
        all_good = False

print("=" * 20)
if all_good:
    print("SUCCESS: Task completed fully")
    print("Both required files generated")
else:
    print("FAILURE: Missing files")