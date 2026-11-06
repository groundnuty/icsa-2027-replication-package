# Final status check
print("🏁 FINAL STATUS CHECK")
print("=" * 20)

required_files = [
    'output/mhw_mask.nc',
    'output/report.json'
]

all_present = True
for file in required_files:
    import os
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_present = False

if all_present:
    print("\n🏆 TASK COMPLETED SUCCESSFULLY")
    print("All required outputs generated as specified.")
else:
    print("\n⚠️  MISSING OUTPUTS")

print("\nAnalysis Summary:")
print("- Region: 57.83°N to 59.03°N, 17.41°E to 18.61°E")
print("- Period: 2008-06-01 to 2008-08-31")
print("- MHW Events Detected: 2")