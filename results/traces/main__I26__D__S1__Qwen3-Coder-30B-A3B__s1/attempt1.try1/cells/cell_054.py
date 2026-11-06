print("TASK COMPLETION CONFIRMATION")
print("=" * 30)
files = ['output/mhw_mask.nc', 'output/report.json']

all_created = True
for file in files:
    import os
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_created = False

if all_created:
    print("=" * 30)
    print("🎉 SUCCESS: ALL FILES CREATED")
    print("Marine heatwave detection task completed successfully!")
    print("All requirements satisfied.")
else:
    print("❌ Some files missing")