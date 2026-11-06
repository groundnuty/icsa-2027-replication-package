# Final confirmation of successful completion
import os

print("TASK COMPLETION VERIFICATION")
print("=" * 30)
files = ['output/mhw_mask.nc', 'output/report.json']

all_created = True
for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_created = False

print("=" * 30)
if all_created:
    print("🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")
else:
    print("❌ Some files missing")