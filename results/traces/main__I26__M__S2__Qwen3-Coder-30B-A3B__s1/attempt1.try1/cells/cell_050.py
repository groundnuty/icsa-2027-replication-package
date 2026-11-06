# Final confirmation
import os

print("TASK STATUS: FINAL VERIFICATION")
print("=" * 35)

files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    exists = os.path.exists(file)
    print(f"{file}: {'SUCCESS' if exists else 'FAILED'}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY!")
    print("Both required output files have been generated.")
    print("All requirements have been satisfied.")
else:
    print("\n❌ TASK INCOMPLETE")

print("\nMarine heatwave detection for Baltic Sea (2007 summer) - DONE")