# Final verification that both files exist
import os

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

print("Final verification of generated files:")
all_exist = True
for file_path in files:
    exists = os.path.exists(file_path)
    print(f"{'✅' if exists else '❌'} {os.path.basename(file_path)}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY!")
    print("Both required files have been generated as specified.")
else:
    print("\n❌ Some files are missing.")