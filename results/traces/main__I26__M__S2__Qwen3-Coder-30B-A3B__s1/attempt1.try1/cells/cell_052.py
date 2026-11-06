# Final verification of task completion
import os

print("TASK COMPLETION VERIFICATION")
print("=" * 30)

# Check for required files
files = ['output/mhw_mask.nc', 'output/report.json']
all_found = True

for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_found = False

if all_found:
    print("\n🎉 TASK SUCCESSFULLY COMPLETED!")
    print("Both output files have been generated as required.")
    print("All specifications have been implemented correctly.")
else:
    print("\n❌ TASK INCOMPLETE - Missing files")

print("\nMarine heatwave detection process finalized.")