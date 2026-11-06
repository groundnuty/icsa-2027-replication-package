# Final verification
print("🏁 FINAL VERIFICATION COMPLETE")
print("=" * 30)

import os

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_exist = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - EXISTS")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        all_exist = False

print("=" * 30)
if all_exist:
    print("🎉 ALL REQUIRED FILES GENERATED")
    print("Task execution completed successfully.")
else:
    print("💥 SOME FILES ARE MISSING")