# Final confirmation
import os

print("📋 FINAL CONFIRMATION")
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
    print("🎉 TASK SUCCESSFULLY COMPLETED")
    print("All output files generated as required")
else:
    print("❌ Some files missing")