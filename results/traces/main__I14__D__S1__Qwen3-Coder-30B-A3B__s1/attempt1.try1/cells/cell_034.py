# Final verification of output files
import os

print("📋 FINAL OUTPUT VERIFICATION")
print("=" * 35)

required_files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_present = True
for file_path in required_files:
    present = os.path.exists(file_path)
    status = "✅" if present else "❌"
    filename = os.path.basename(file_path)
    print(f"{status} {filename}")
    if not present:
        all_present = False

print("=" * 35)
if all_present:
    print("🎉 ALL REQUIRED FILES GENERATED SUCCESSFULLY")
    print("Task completion verified.")
else:
    print("💥 MISSING FILES DETECTED")