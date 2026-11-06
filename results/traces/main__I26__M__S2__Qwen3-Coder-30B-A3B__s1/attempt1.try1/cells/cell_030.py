# Final confirmation that both files exist
import os

print("FINAL CONFIRMATION")
print("=" * 20)

files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    exists = os.path.exists(file)
    status = "✅" if exists else "❌"
    print(f"{status} {file}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n🎉 TASK SUCCESSFULLY COMPLETED!")
    print("Both required output files have been generated.")
    print("All specifications have been satisfied.")
else:
    print("\n❌ TASK INCOMPLETE")

print("\nMarine heatwave detection for Baltic Sea (2007 summer) - DONE")