# Final verification that both required files exist
import os

required_files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file_path in required_files:
    if not os.path.exists(file_path):
        print(f"ERROR: {file_path} not found")
        all_exist = False
    else:
        print(f"✓ {file_path} exists")

if all_exist:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY!")
    print("All required files have been generated as specified.")
else:
    print("\n❌ Some files are missing!")