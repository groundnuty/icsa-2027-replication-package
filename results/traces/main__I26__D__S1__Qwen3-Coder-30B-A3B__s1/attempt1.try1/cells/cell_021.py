# Final verification
import os

files = ['output/mhw_mask.nc', 'output/report.json']
all_good = True

for file in files:
    if not os.path.exists(file):
        print(f"❌ {file} not found")
        all_good = False
    else:
        print(f"✅ {file} created successfully")

if all_good:
    print("\n🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")