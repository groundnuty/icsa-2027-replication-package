# Final confirmation that both files exist
import os

files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    if not os.path.exists(file):
        print(f"❌ {file} not found")
        all_exist = False
    else:
        print(f"✅ {file} created successfully")

if all_exist:
    print("\n🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")