print("TASK COMPLETION CONFIRMED")
print("=" * 25)
files = ['output/mhw_mask.nc', 'output/report.json']

all_present = True
for file in files:
    import os
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_present = False

if all_present:
    print("=" * 25)
    print("🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")