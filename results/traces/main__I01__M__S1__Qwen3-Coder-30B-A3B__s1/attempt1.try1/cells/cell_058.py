# Final verification that both files exist
import os

print("FINAL VERIFICATION")
print("=" * 20)
files = ["output/mhw_mask.nc", "output/report.json"]

success = True
for file in files:
    exists = os.path.exists(file)
    print(f"{file}: {'OK' if exists else 'ERROR'}")
    if not exists:
        success = False

print("=" * 20)
if success:
    print("🎉 TASK COMPLETED SUCCESSFULLY")
    print("✅ All required files created")
else:
    print("❌ Some files missing")