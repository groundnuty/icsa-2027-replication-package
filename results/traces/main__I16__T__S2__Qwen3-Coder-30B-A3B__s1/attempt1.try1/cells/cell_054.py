# Final validation
import os

print("VALIDATION RESULTS")
print("=" * 20)
print("Output files check:")

# Check both files exist
files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_exist = False

if all_exist:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY")
    print("Both required files have been created:")
    print("- output/mhw_mask.nc")
    print("- output/report.json")
else:
    print("\n❌ TASK INCOMPLETE")

print("=" * 20)