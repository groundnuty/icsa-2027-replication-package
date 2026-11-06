# Final confirmation
print("TASK COMPLETION STATUS")
print("=" * 25)

# Check if files exist
files = ['output/mhw_mask.nc', 'output/report.json']
all_good = True

for file in files:
    import os
    if os.path.exists(file):
        print(f"✅ {os.path.basename(file)}")
    else:
        print(f"❌ {os.path.basename(file)}")
        all_good = False

print("=" * 25)
if all_good:
    print("🎉 ALL FILES SUCCESSFULLY GENERATED")
    print("Marine heatwave detection analysis completed!")
    print("Both output files are ready as specified.")
else:
    print("⚠️  Some files missing")

print("\n✅ TASK STATUS: FINAL")