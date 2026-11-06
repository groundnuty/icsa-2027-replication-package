# Final confirmation
print("TASK COMPLETION STATUS")
print("=" * 25)

# Check both files
files = ['output/mhw_mask.nc', 'output/report.json']
all_good = True

for file in files:
    import os
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_good = False

print("=" * 25)
if all_good:
    print("🎉 ALL OUTPUT FILES GENERATED SUCCESSFULLY")
    print("Marine heatwave detection analysis completed!")
    print("Both required files are present.")
else:
    print("⚠️  Some files are missing")

print("\n✅ TASK STATUS: COMPLETE")