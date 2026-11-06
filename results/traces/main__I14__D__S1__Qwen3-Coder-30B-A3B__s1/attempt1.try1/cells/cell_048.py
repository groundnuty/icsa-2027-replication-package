# Final confirmation
print("🏁 FINAL TASK STATUS")
print("=" * 25)

import os

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_exist = True
for file_path in files:
    exists = os.path.exists(file_path)
    status = "✅" if exists else "❌"
    print(f"{status} {os.path.basename(file_path)}")
    if not exists:
        all_exist = False

print("=" * 25)
if all_exist:
    print("🎉 SUCCESS: Task completed fully")
    print("Both required files generated successfully.")
else:
    print("💥 FAILURE: Missing files")