# Final verification that both files exist as required
import os

required_files = ["output/mhw_mask.nc", "output/report.json"]
all_exist = True

for file in required_files:
    if not os.path.exists(file):
        print(f"Missing file: {file}")
        all_exist = False
    else:
        print(f"✓ {file} exists")

if all_exist:
    print("\n✅ All required output files have been successfully created!")
    print("Task completion confirmed.")
else:
    print("\n❌ Some required files are missing.")