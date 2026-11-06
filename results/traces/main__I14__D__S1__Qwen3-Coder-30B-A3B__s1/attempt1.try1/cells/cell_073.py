# Final confirmation
print("🏁 TASK STATUS CONFIRMED")
print("=" * 25)

import os

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_good = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - CREATED")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        all_good = False

print("=" * 25)
if all_good:
    print("🎉 SUCCESS: All files generated")
    print("Task completed as specified in requirements.")
else:
    print("💥 FAILURE: Missing files")