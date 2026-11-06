# Final confirmation that both files exist
import os

print("FINAL VERIFICATION")
print("=" * 16)
files = ['output/mhw_mask.nc', 'output/report.json']

all_exist = True
for file in files:
    exists = os.path.exists(file)
    status = "✅" if exists else "❌"
    print(f"{status} {file}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n🎊 TASK SUCCESSFULLY COMPLETED")
    print("Both required output files have been generated.")
    print("Marine heatwave analysis for Baltic Sea region is finished.")
else:
    print("\n⚠️  TASK INCOMPLETE - MISSING FILES")