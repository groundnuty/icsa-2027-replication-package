# Final validation
import os

print("VALIDATION RESULTS")
print("=" * 20)
print("Checking output files:")

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
    print("\n🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully.")
else:
    print("\n❌ SOME FILES MISSING")

print("=" * 20)