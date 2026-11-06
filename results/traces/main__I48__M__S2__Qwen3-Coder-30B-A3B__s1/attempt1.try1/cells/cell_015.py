# Confirm final state
import os

print("🔍 FINAL STATE CONFIRMATION")
print("=" * 30)

required_files = [
    'output/mhw_mask.nc',
    'output/report.json'
]

all_files_exist = True
for file_path in required_files:
    exists = os.path.exists(file_path)
    status = "✅ FOUND" if exists else "❌ MISSING"
    print(f"{file_path:<25} {status}")
    if not exists:
        all_files_exist = False

print("\n" + "=" * 30)
if all_files_exist:
    print("🎉 ALL REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")
else:
    print("❌ MISSING FILES - TASK INCOMPLETE")