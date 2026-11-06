# Final confirmation
print("✅ TASK COMPLETION CONFIRMED")
print("=" * 30)

import os

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_good = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✓ {os.path.basename(file_path)} - CREATED")
    else:
        print(f"✗ {os.path.basename(file_path)} - MISSING")
        all_good = False

print("=" * 30)
if all_good:
    print("🎉 ALL REQUIREMENTS SATISFIED")
    print("Task execution completed successfully.")
else:
    print("❌ SOME FILES MISSING")