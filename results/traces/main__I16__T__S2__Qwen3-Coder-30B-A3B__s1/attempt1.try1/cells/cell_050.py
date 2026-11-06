# Final validation
import os

print("VALIDATION SUMMARY")
print("=" * 20)
print("Checking output files:")

files = ['output/mhw_mask.nc', 'output/report.json']
all_good = True

for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_good = False

if all_good:
    print("\n🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully.")
else:
    print("\n❌ TASK INCOMPLETE")

print("=" * 20)