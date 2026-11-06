# Final verification
print("VALIDATION COMPLETE")
print("=" * 20)

import os

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_good = True
for file_path in files:
    exists = os.path.exists(file_path)
    print(f"{'✅' if exists else '❌'} {os.path.basename(file_path)}")
    if not exists:
        all_good = False

print("=" * 20)
if all_good:
    print("🎉 ALL FILES SUCCESSFULLY GENERATED")
    print("Task execution completed successfully.")
else:
    print("💥 SOME FILES MISSING")