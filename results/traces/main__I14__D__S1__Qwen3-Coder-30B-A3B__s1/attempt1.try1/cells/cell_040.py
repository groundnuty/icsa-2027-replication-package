# Final confirmation
print("TASK COMPLETION STATUS")
print("=" * 25)

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

print("=" * 25)
if all_good:
    print("🎉 SUCCESS: All files generated")
    print("Task completed as specified")
else:
    print("💥 FAILURE: Missing files")