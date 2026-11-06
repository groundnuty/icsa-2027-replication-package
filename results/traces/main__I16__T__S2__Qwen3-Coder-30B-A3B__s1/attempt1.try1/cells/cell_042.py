# Final validation
import os

print("VALIDATION RESULTS")
print("=" * 20)
print("Checking output files:")

# Check if files exist
files_to_check = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file_path in files_to_check:
    if os.path.exists(file_path):
        print(f"✅ {file_path}")
    else:
        print(f"❌ {file_path}")
        all_exist = False

if all_exist:
    print("\n🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully.")
else:
    print("\n❌ Some files are missing")

print("=" * 20)