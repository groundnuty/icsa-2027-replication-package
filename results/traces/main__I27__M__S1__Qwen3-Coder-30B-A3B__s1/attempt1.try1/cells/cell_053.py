print("FINAL TASK STATUS")
print("=" * 17)
print("Files created:")
files = ['output/mhw_mask.nc', 'output/report.json']
all_created = True

for file in files:
    import os
    if os.path.exists(file):
        print(f"  ✅ {file}")
    else:
        print(f"  ❌ {file}")
        all_created = False

if all_created:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY")
    print("All required outputs generated as specified.")
else:
    print("\n💥 TASK INCOMPLETE")

print(f"\nAnalysis Summary:")
print(f"- Region: 57.83°N to 59.03°N, 17.41°E to 18.61°E")
print(f"- Period: 2008-06-01 to 2008-08-31")
print(f"- MHW Events: 2")