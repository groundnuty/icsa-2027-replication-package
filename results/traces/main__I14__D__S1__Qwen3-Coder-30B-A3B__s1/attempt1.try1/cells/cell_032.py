# Final verification that both files exist
import os

print("📋 FINAL VERIFICATION")
print("=" * 25)

files_to_check = [
    ('/work/output/mhw_mask.nc', 'MHW Mask File'),
    ('/work/report.json', 'Report File')
]

all_exist = True
for file_path, description in files_to_check:
    exists = os.path.exists(file_path)
    status = "✅" if exists else "❌"
    print(f"{status} {description}")
    if not exists:
        all_exist = False

print("=" * 25)
if all_exist:
    print("🎉 ALL FILES SUCCESSFULLY GENERATED")
    print("Task completion confirmed.")
else:
    print("💥 SOME FILES MISSING")