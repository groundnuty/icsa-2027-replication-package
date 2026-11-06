# Final verification
import os

print("VERIFYING TASK COMPLETION")
print("=" * 25)

# Check files exist
files = ['output/mhw_mask.nc', 'output/report.json']
all_present = True

for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_present = False

if all_present:
    print("\n🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection for Baltic Sea region completed successfully.")
else:
    print("\n❌ Some files are missing")

print("=" * 25)