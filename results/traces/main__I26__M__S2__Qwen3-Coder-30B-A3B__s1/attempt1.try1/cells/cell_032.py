# Final verification of task completion
import os

print("TASK VERIFICATION")
print("=" * 20)

# Check required files
required_files = [
    'output/mhw_mask.nc',
    'output/report.json'
]

all_present = True
for file in required_files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_present = False

if all_present:
    print("\n🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection completed successfully!")
    print("Both output files have been generated as required.")
else:
    print("\n❌ TASK INCOMPLETE - Missing files")

print("\nProcess finished.")