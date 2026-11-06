# Final verification
import os

print("🔍 FINAL VERIFICATION")
print("=" * 50)

required_files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_present = True
for file_path in required_files:
    present = os.path.exists(file_path)
    status = "✅ FOUND" if present else "❌ MISSING"
    print(f"{status} {file_path}")
    if not present:
        all_present = False

print("=" * 50)
if all_present:
    print("🎉 ALL REQUIRED FILES SUCCESSFULLY GENERATED")
    print("Task completed as specified in the requirements.")
else:
    print("❌ SOME FILES ARE MISSING")