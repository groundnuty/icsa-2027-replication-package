# Final confirmation that both files exist
import os

print("FINAL FILE VERIFICATION")
print("=" * 23)
files = ['output/mhw_mask.nc', 'output/report.json']

all_exist = True
for file in files:
    exists = os.path.exists(file)
    print(f"{'✅' if exists else '❌'} {file}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n🏆 TASK COMPLETED SUCCESSFULLY")
    print("All required output files have been generated.")
    print("Marine heatwave analysis for Baltic Sea region is finished.")
else:
    print("\n💥 TASK INCOMPLETE")

print(f"\n📋 ANALYSIS SUMMARY:")
print(f"   Region: 57.83°N to 59.03°N, 17.41°E to 18.61°E")
print(f"   Period: 2008-06-01 to 2008-08-31")
print(f"   Events: 2")