# Final verification
print("🏁 FINAL STATUS")
print("=" * 20)

import os

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_exist = True
for file_path in files:
    exists = os.path.exists(file_path)
    status = "✅" if exists else "❌"
    print(f"{status} {os.path.basename(file_path)}")
    if not exists:
        all_exist = False

print("=" * 20)
if all_exist:
    print("🎉 TASK COMPLETED SUCCESSFULLY")
    print("Both required files generated.")
else:
    print("💥 TASK INCOMPLETE")