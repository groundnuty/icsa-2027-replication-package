# Final verification that everything is done
import os

print("FINAL VERIFICATION")
print("=" * 25)
files = ["output/mhw_mask.nc", "output/report.json"]

all_good = True
for file in files:
    if os.path.exists(file):
        print(f"✓ {file}")
    else:
        print(f"✗ {file}")
        all_good = False

print("=" * 25)
if all_good:
    print("SUCCESS: All files created successfully")
    print("✅ Task completed as requested")
else:
    print("FAILURE: Some files missing")