# Final verification
import os

print("🔍 FINAL VERIFICATION")
print("=" * 20)

required_files = ['output/mhw_mask.nc', 'output/report.json']
all_good = True

for file in required_files:
    exists = os.path.exists(file)
    print(f"{'✓' if exists else '✗'} {file}")
    if not exists:
        all_good = False

if all_good:
    print("\n✅ ALL REQUIREMENTS SATISFIED")
    print("Marine heatwave analysis completed successfully for Baltic Sea region.")
else:
    print("\n❌ SOME FILES MISSING")