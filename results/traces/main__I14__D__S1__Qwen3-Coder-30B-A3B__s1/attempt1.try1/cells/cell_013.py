# Final verification that both required files exist
import os

required_files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_exist = True
for file_path in required_files:
    if not os.path.exists(file_path):
        print(f"Missing required file: {file_path}")
        all_exist = False
    else:
        print(f"✓ {file_path} exists")

if all_exist:
    print("\n✅ Task completed successfully!")
    print("Both required files have been generated as specified.")
else:
    print("\n❌ Some required files are missing.")