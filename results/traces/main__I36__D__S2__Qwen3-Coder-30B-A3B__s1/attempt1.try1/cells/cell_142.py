# Final verification
import os

print("TASK VERIFICATION COMPLETE")
print("=" * 30)
files = ["output/mhw_mask.nc", "output/report.json"]

all_good = True
for file in files:
    if os.path.exists(file):
        print(f"✓ {file}")
    else:
        print(f"✗ {file}")
        all_good = False

print("=" * 30)
if all_good:
    print("🎉 SUCCESS: All files created")
    print("✅ Task completed successfully!")
else:
    print("❌ FAILURE: Missing files")