# Final verification that both files exist
import os

print("📋 FINAL VERIFICATION")
print("=" * 20)

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
    print("All required files generated as specified.")
else:
    print("💥 TASK INCOMPLETE")