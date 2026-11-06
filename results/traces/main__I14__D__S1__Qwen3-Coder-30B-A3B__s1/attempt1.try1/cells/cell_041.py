# Final check of output files
print("🔍 OUTPUT FILE VERIFICATION")
print("=" * 30)

import os

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_exist = True
for file_path in files:
    exists = os.path.exists(file_path)
    print(f"{'✅' if exists else '❌'} {os.path.basename(file_path)}")
    if not exists:
        all_exist = False

print("=" * 30)
if all_exist:
    print("🎉 ALL REQUIRED FILES SUCCESSFULLY CREATED")
    print("Task execution completed successfully.")
else:
    print("💥 SOME FILES ARE MISSING")