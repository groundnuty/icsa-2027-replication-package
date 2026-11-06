# Final confirmation
print("🏁 TASK STATUS")
print("=" * 20)

import os

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_exist = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - CREATED")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        all_exist = False

print("=" * 20)
if all_exist:
    print("🎉 SUCCESS: All files generated")
    print("Task completed successfully.")
else:
    print("💥 FAILURE: Missing files")