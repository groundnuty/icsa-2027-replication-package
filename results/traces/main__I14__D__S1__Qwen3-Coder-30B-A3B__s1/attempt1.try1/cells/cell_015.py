# Verify final state
import os

print("Final verification:")
files_to_check = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_good = True
for file_path in files_to_check:
    exists = os.path.exists(file_path)
    print(f"✓ {file_path}: {'Exists' if exists else 'Missing'}")
    if not exists:
        all_good = False

if all_good:
    print("\n🎉 All required files successfully created!")
    print("Task completed as specified.")
else:
    print("\n❌ Some files are missing.")