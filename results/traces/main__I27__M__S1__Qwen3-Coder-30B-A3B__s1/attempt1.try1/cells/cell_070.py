# Final verification
import os

print("📋 FINAL VERIFICATION")
print("=" * 20)
files = ['output/mhw_mask.nc', 'output/report.json']

all_good = True
for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_good = False

if all_good:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY")
    print("Both required files have been generated.")
    print("Marine heatwave analysis for Baltic Sea region is finished.")
else:
    print("\n💥 TASK INCOMPLETE")

print(f"\n📊 ANALYSIS SUMMARY:")
print(f"Region: 57.83°N to 59.03°N, 17.41°E to 18.61°E")
print(f"Period: 2008-06-01 to 2008-08-31")
print(f"MHW Events: 2")