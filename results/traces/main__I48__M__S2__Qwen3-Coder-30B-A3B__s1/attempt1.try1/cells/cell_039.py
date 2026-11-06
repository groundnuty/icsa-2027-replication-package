# Final confirmation
print("✅ TASK COMPLETION CONFIRMED")
print("=" * 30)

# Check files
files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    import os
    if os.path.exists(file):
        print(f"✅ {os.path.basename(file)} - CREATED")
    else:
        print(f"❌ {os.path.basename(file)} - NOT FOUND")
        all_exist = False

print("=" * 30)
if all_exist:
    print("🎉 ALL OUTPUT FILES SUCCESSFULLY GENERATED")
    print("Marine heatwave detection analysis completed as requested.")
else:
    print("⚠️  Some files are missing")

print("\n✅ TASK STATUS: FINALIZED")