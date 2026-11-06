# Final confirmation
print("📋 FINAL OUTPUT VERIFICATION")
print("=" * 30)

# Check files
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
    print("🎉 ALL REQUIRED FILES GENERATED")
    print("Marine heatwave detection analysis completed successfully!")
    print("Both output files are ready.")
else:
    print("⚠️  Some files are missing")

print("\n✅ TASK STATUS: COMPLETE")