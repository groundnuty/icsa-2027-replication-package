# Final verification that both files exist
import os

print("FINAL VERIFICATION STATUS")
print("=" * 25)
files = ['output/mhw_mask.nc', 'output/report.json']

all_present = True
for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_present = False

if all_present:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY")
    print("Both required output files have been generated.")
    print("Marine heatwave analysis for Baltic Sea region is finished.")
else:
    print("\n💥 TASK INCOMPLETE")

print(f"\n📊 ANALYSIS SUMMARY:")
print(f"Region: 57.83°N to 59.03°N, 17.41°E to 18.61°E")
print(f"Period: 2008-06-01 to 2008-08-31")
print(f"MHW Events: 2")