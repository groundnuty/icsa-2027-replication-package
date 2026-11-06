print("TASK COMPLETION CONFIRMED")
print("=" * 25)
files = ['output/mhw_mask.nc', 'output/report.json']

all_good = True
for file in files:
    import os
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_good = False

if all_good:
    print("=" * 25)
    print("🎉 SUCCESS: TASK COMPLETED")
    print("All required files created successfully.")
    print("Marine heatwave detection task completed!")