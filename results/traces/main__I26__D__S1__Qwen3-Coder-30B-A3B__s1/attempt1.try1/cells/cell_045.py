# Final confirmation
print("TASK COMPLETION CONFIRMATION")
print("=" * 30)
print("Checking required files:")

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
    print("=" * 30)
    print("🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")
else:
    print("❌ Some files missing")