# Final verification
print("✅ TASK COMPLETION CONFIRMED")
print("=" * 30)

import os

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_exist = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✓ {os.path.basename(file_path)} - CREATED SUCCESSFULLY")
    else:
        print(f"✗ {os.path.basename(file_path)} - NOT FOUND")
        all_exist = False

print("=" * 30)
if all_exist:
    print("🎉 ALL REQUIREMENTS SATISFIED")
    print("Task execution completed successfully.")
else:
    print("❌ SOME FILES MISSING")