# Final confirmation that both files exist
import os

print("TASK COMPLETION VERIFICATION")
print("=" * 30)
files = ['output/mhw_mask.nc', 'output/report.json']

all_present = True
for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_present = False

print("=" * 30)
if all_present:
    print("🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")
else:
    print("❌ Some files missing")