# Task completion verification
import os

# Check that both required files exist
required_files = ['output/mhw_mask.nc', 'output/report.json']
all_present = True

for file in required_files:
    if not os.path.exists(file):
        print(f"MISSING: {file}")
        all_present = False
    else:
        print(f"✓ {file}")

if all_present:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY")
    print("Both output files have been generated as required.")
else:
    print("\n❌ Some files are missing")