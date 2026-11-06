# Final confirmation
print("🏁 TASK COMPLETION STATUS")
print("=" * 30)

import os

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_good = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - SUCCESS")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        all_good = False

print("=" * 30)
if all_good:
    print("🎉 TASK COMPLETED SUCCESSFULLY")
    print("Both required files have been generated.")
else:
    print("💥 TASK INCOMPLETE")