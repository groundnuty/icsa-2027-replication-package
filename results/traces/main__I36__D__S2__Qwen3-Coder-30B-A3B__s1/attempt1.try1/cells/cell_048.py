# Final verification
import os

print("✅ FINAL VERIFICATION ✅")
print("=" * 25)
required_files = ["output/mhw_mask.nc", "output/report.json"]

all_created = True
for file in required_files:
    if os.path.exists(file):
        print(f"✓ {file}")
    else:
        print(f"✗ {file}")
        all_created = False

print("=" * 25)
if all_created:
    print("🎉 SUCCESS: All files created")
    print("✅ Task completed as requested")
else:
    print("❌ FAILURE: Some files missing")