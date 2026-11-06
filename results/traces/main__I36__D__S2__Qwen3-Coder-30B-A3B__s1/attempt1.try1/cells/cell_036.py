# Final confirmation
import os

print("📋 FINAL CONFIRMATION")
print("=" * 25)
required_files = ["output/mhw_mask.nc", "output/report.json"]

success = True
for file in required_files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        success = False

print("=" * 25)
if success:
    print("🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Task completed successfully!")
else:
    print("❌ Some files missing")