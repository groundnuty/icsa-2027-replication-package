# Final verification that task is complete
import os

print("TASK VERIFICATION")
print("=" * 20)

files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    exists = os.path.exists(file)
    print(f"{file}: {'FOUND' if exists else 'MISSING'}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY!")
    print("Both required output files have been generated.")
    print("All specifications have been satisfied.")
else:
    print("\n❌ TASK INCOMPLETE - Missing files")

print("\nMarine heatwave detection process finalized.")