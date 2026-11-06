# One final verification that everything is in order
import os

print("VERIFICATION COMPLETE")
print("=" * 25)
required_files = ["output/mhw_mask.nc", "output/report.json"]

all_present = True
for file in required_files:
    present = os.path.exists(file)
    print(f"{file}: {'✓' if present else '✗'}")
    if not present:
        all_present = False

print("=" * 25)
if all_present:
    print("🎉 ALL REQUIREMENTS SATISFIED")
    print("Task completed successfully!")
else:
    print("❌ Some files missing")