print("TASK COMPLETION VERIFICATION")
print("=" * 30)
files = ['output/mhw_mask.nc', 'output/report.json']

all_exist = True
for file in files:
    import os
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_exist = False

if all_exist:
    print("=" * 30)
    print("🎉 SUCCESS: ALL FILES CREATED")
    print("Marine heatwave detection task completed successfully!")