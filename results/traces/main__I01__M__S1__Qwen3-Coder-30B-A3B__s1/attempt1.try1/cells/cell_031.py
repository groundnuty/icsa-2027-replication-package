# Final verification
print("FINAL VERIFICATION")
print("=" * 20)
print("Checking output files:")

import os
files = ["output/mhw_mask.nc", "output/report.json"]

success = True
for file in files:
    exists = os.path.exists(file)
    print(f"  {file}: {'✓' if exists else '✗'}")
    if not exists:
        success = False

print("=" * 20)
if success:
    print("🎉 ALL FILES CREATED SUCCESSFULLY")
    print("✅ TASK COMPLETED")
else:
    print("❌ SOME FILES MISSING")