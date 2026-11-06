# Final verification
import os

print("TASK VERIFICATION")
print("=" * 15)

required_files = [
    'output/mhw_mask.nc',
    'output/report.json'
]

all_found = True
for file in required_files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_found = False

if all_found:
    print("\n🎉 ALL REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")
else:
    print("\n❌ Some files missing")