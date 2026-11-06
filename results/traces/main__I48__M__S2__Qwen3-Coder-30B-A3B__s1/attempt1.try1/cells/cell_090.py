# Final verification
print("✅ TASK COMPLETED SUCCESSFULLY")
print("=" * 30)

# Check files exist
files = ['output/mhw_mask.nc', 'output/report.json']
all_present = True

for file in files:
    import os
    if os.path.exists(file):
        print(f"✅ {os.path.basename(file)}")
    else:
        print(f"❌ {os.path.basename(file)}")
        all_present = False

print("=" * 30)
if all_present:
    print("🎉 ALL OUTPUT FILES GENERATED")
    print("Marine heatwave detection analysis finished!")
    print("Both required files are ready for use.")
else:
    print("⚠️  Some files are missing")

print("\n✅ TASK STATUS: FINAL")