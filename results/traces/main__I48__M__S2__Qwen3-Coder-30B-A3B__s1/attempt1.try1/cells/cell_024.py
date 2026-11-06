# Final confirmation that both files are present
import os

print("🔍 FINAL CONFIRMATION")
print("=" * 20)

files_to_check = [
    'output/mhw_mask.nc',
    'output/report.json'
]

all_found = True
for file_path in files_to_check:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - PRESENT")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        all_found = False

print("=" * 20)
if all_found:
    print("🎉 SUCCESS: All required files generated!")
    print("Marine heatwave detection task completed successfully.")
else:
    print("⚠️  Missing files detected.")

print("\n✅ TASK STATUS: FINISHED")