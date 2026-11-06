# Clean up any temporary files if needed
import os
import shutil

# Check if we have the required files
required_files = ['output/mhw_mask.nc', 'output/report.json']

all_present = True
for file in required_files:
    if not os.path.exists(file):
        print(f"Missing file: {file}")
        all_present = False

if all_present:
    print("✅ All required output files are present")
    print("Task completed successfully!")
else:
    print("❌ Some required files are missing")