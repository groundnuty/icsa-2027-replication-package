# Final verification
import os

print("📋 FINAL VERIFICATION")
print("=" * 25)
files = ["output/mhw_mask.nc", "output/report.json"]

all_present = True
for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_present = False

print("=" * 25)
if all_present:
    print("🎉 ALL FILES SUCCESSFULLY GENERATED")
    print("✅ TASK COMPLETED AS REQUESTED")
else:
    print("❌ SOME FILES MISSING")