# Final confirmation
print("TASK COMPLETION STATUS")
print("=" * 25)

# Check if files exist
files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    import os
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_exist = False

print("=" * 25)
if all_exist:
    print("🎉 ALL FILES SUCCESSFULLY GENERATED")
    print("Marine heatwave detection analysis completed!")
else:
    print("⚠️  Some files missing")

print("\n✅ TASK FINISHED")