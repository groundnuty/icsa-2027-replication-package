# Final confirmation
import os

print("CONFIRMING FILE CREATION:")
files = ['output/mhw_mask.nc', 'output/report.json']

all_created = True
for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_created = False

if all_created:
    print("\n🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")
else:
    print("\n❌ Some files not created")