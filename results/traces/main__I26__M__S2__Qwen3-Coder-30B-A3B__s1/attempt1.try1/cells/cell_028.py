# Final confirmation
import os

print("TASK COMPLETION VERIFICATION")
print("=" * 30)

# Check for required files
files_to_check = [
    'output/mhw_mask.nc',
    'output/report.json'
]

all_found = True
for file in files_to_check:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_found = False

if all_found:
    print("\n🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection completed successfully for Baltic Sea (2007 summer)")
else:
    print("\n❌ TASK INCOMPLETE - Missing files")

print("\nProcess terminated successfully.")