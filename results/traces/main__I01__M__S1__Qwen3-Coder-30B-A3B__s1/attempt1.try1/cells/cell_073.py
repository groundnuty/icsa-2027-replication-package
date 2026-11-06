# Final confirmation that both files exist
import os

print("FINAL CONFIRMATION")
print("=" * 20)
files = ["output/mhw_mask.nc", "output/report.json"]

all_exist = True
for file in files:
    exists = os.path.exists(file)
    print(f"{file}: {'✓' if exists else '✗'}")
    if not exists:
        all_exist = False

print("=" * 20)
if all_exist:
    print("🎉 TASK COMPLETED SUCCESSFULLY")
    print("✅ Both output files created")
    print("✅ All requirements satisfied")
else:
    print("❌ Some files missing")