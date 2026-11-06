# Final verification
print("🏁 FINAL STATUS CHECK")
print("=" * 25)

import os

required_files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_created = True
for file_path in required_files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - SUCCESS")
    else:
        print(f"❌ {os.path.basename(file_path)} - FAILED")
        all_created = False

print("=" * 25)
if all_created:
    print("🎉 TASK COMPLETED SUCCESSFULLY")
    print("Both output files generated correctly.")
else:
    print("💥 TASK INCOMPLETE")