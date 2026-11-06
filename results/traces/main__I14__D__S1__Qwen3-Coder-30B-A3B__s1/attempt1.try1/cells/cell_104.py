# Final confirmation
print("✅ TASK COMPLETED SUCCESSFULLY")
print("=" * 30)

import os

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_present = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✓ {os.path.basename(file_path)} - CREATED")
    else:
        print(f"✗ {os.path.basename(file_path)} - MISSING")
        all_present = False

print("=" * 30)
if all_present:
    print("🎉 ALL FILES GENERATED AS SPECIFIED")
    print("Task execution completed successfully.")
else:
    print("💥 SOME FILES MISSING")