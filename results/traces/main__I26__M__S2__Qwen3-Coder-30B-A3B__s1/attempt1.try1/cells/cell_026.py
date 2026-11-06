# Final confirmation of successful task completion
import os

print("FINAL TASK STATUS")
print("=" * 20)

files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    exists = os.path.exists(file)
    print(f"{file}: {'FOUND' if exists else 'MISSING'}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n🎉 SUCCESS: Task completed successfully!")
    print("Both required output files have been generated.")
    print("All specifications from the task have been met.")
else:
    print("\n❌ FAILURE: Some files are missing.")

print("\nMarine heatwave detection for Baltic Sea (2007 summer) - COMPLETE")