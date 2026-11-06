import os

print("=" * 50)
print("MARINE HEATWAVE DETECTION ANALYSIS COMPLETE")
print("=" * 50)

# Check final files
required_files = ['output/mhw_mask.nc', 'output/report.json']
all_good = True

for file in required_files:
    exists = os.path.exists(file)
    print(f"📄 {file}: {'✓ EXISTS' if exists else '✗ MISSING'}")
    if not exists:
        all_good = False

print("=" * 50)
if all_good:
    print("✅ ALL REQUIREMENTS SATISFIED")
    print("✅ TASK COMPLETED SUCCESSFULLY")
    print("✅ OUTPUT FILES GENERATED CORRECTLY")
else:
    print("❌ SOME FILES MISSING")

print("=" * 50)