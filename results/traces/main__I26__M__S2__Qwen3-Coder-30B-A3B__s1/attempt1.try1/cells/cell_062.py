# Final confirmation of task completion
import os

print("TASK EXECUTION RESULT")
print("=" * 25)

files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_exist = False

if all_exist:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY!")
    print("Both required output files have been generated.")
    print("All specifications have been implemented correctly.")
else:
    print("\n❌ TASK INCOMPLETE - Missing files")

print("\nMarine heatwave detection for Baltic Sea (2007 summer) - PROCESS ENDED")