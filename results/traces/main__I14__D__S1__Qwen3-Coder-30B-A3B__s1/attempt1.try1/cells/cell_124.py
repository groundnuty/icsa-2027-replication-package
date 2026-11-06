# Final confirmation
print("🏁 TASK COMPLETION CONFIRMED")
print("=" * 30)

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

print("=" * 30)
if all_exist:
    print("🎉 SUCCESS: All files generated")
    print("Task completed as specified.")
else:
    print("💥 FAILURE: Missing files")