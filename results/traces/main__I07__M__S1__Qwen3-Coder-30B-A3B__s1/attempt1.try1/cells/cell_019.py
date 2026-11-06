# Final task verification
import os

print("FINAL TASK VERIFICATION")
print("=" * 25)
print("Required files:")
files = ["output/mhw_mask.nc", "output/report.json"]
all_good = True

for file in files:
    if os.path.exists(file):
        print(f"✓ {file}")
    else:
        print(f"✗ {file}")
        all_good = False

if all_good:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY!")
    print("All required outputs have been generated.")
else:
    print("\n❌ Some files are missing.")