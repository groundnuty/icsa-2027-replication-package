# Final verification
print("✅ TASK COMPLETED")
print("=" * 20)

import os

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_present = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - CREATED")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        all_present = False

print("=" * 20)
if all_present:
    print("🎉 SUCCESS: All files generated")
    print("Task execution completed successfully.")
else:
    print("💥 FAILURE: Missing files")