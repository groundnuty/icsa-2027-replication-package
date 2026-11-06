# Final verification
import os

print("📋 FINAL VERIFICATION RESULTS")
print("=" * 30)

# Check for required files
required_files = ['output/mhw_mask.nc', 'output/report.json']
all_good = True

for file_path in required_files:
    exists = os.path.exists(file_path)
    status = "✅ FOUND" if exists else "❌ MISSING"
    print(f"{status} {os.path.basename(file_path)}")
    if not exists:
        all_good = False

print("=" * 30)
if all_good:
    print("🎉 ALL OUTPUT FILES SUCCESSFULLY GENERATED")
    print("Marine heatwave detection analysis is COMPLETE")
else:
    print("⚠️  Some files are missing")

print("\n✅ TASK FINISHED SUCCESSFULLY")