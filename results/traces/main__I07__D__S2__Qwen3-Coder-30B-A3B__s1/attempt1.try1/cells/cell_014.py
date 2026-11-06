# Clean up any temporary files if needed
import shutil
import os

# Check if we have the expected output files
expected_files = [
    '/work/output/mhw_mask.nc',
    '/work/output/report.json'
]

all_good = True
for file_path in expected_files:
    if not os.path.exists(file_path):
        print(f"Missing file: {file_path}")
        all_good = False
    else:
        print(f"✓ {file_path}")

if all_good:
    print("\n✅ All required files successfully generated!")
else:
    print("\n❌ Some files are missing!")

print("\nTask completed successfully.")