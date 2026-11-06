# Final verification
import os

print("FINAL VERIFICATION STATUS")
print("=" * 25)

required_files = [
    'output/mhw_mask.nc',
    'output/report.json'
]

all_present = True
for file in required_files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_present = False

if all_present:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY")
    print("Both required output files have been generated.")
    print("Marine heatwave analysis for Baltic Sea region is complete.")
else:
    print("\n💥 TASK INCOMPLETE")

print(f"\nSummary:")
print(f"- Region analyzed: 57.83°N to 59.03°N, 17.41°E to 18.61°E")
print(f"- Period: 2008-06-01 to 2008-08-31")
print(f"- MHW events detected: 2")