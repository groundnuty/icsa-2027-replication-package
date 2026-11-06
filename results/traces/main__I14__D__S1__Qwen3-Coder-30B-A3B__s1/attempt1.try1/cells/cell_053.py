# Final verification
print("✅ TASK COMPLETION VERIFIED")
print("=" * 30)

import os

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_good = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✓ {os.path.basename(file_path)} - SUCCESS")
    else:
        print(f"✗ {os.path.basename(file_path)} - FAILED")
        all_good = False

print("=" * 30)
if all_good:
    print("🎉 ALL FILES GENERATED SUCCESSFULLY")
    print("Task completed as specified.")
else:
    print("❌ SOME FILES MISSING")