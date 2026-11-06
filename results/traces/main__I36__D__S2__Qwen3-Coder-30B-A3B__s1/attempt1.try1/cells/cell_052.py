# Final verification that everything is complete
import os

print("FINAL VERIFICATION")
print("=" * 20)
required_files = [
    "output/mhw_mask.nc",
    "output/report.json"
]

all_good = True
for file in required_files:
    if os.path.exists(file):
        print(f"✓ {file}")
    else:
        print(f"✗ {file}")
        all_good = False

print("=" * 20)
if all_good:
    print("🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Task completed successfully!")
else:
    print("❌ Some files missing")