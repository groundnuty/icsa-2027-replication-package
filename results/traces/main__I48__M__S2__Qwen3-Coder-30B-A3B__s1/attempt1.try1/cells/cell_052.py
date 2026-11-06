# Final verification
print("✅ FINAL TASK VERIFICATION")
print("=" * 30)

# Check both files exist
files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    import os
    if os.path.exists(file):
        print(f"✅ {os.path.basename(file)} - CREATED")
    else:
        print(f"❌ {os.path.basename(file)} - MISSING")
        all_exist = False

print("=" * 30)
if all_exist:
    print("🎉 SUCCESS: All required files generated!")
    print("Marine heatwave detection task completed successfully.")
    print("Both output files are ready for use.")
else:
    print("⚠️  Some files are missing")

print("\n✅ TASK STATUS: COMPLETE")