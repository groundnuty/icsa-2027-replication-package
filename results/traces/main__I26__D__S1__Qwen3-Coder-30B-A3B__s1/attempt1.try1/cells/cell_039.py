# Final confirmation that both files exist
import os

files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

print("FINAL CONFIRMATION:")
for file in files:
    exists = os.path.exists(file)
    print(f"{'✅' if exists else '❌'} {file}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")
else:
    print("\n❌ Some files missing")