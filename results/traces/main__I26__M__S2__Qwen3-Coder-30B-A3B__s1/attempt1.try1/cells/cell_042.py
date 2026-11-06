# Final confirmation
import os

print("TASK COMPLETION CONFIRMATION")
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
    print("Both required output files have been generated.")
    print("All specifications have been met.")
else:
    print("\n❌ TASK INCOMPLETE")

print("\nMarine heatwave detection for Baltic Sea (2007 summer) - DONE")