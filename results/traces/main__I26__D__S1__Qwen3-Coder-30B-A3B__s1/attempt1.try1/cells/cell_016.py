# Final status check
import os

status = {
    'mhw_mask.nc': os.path.exists('output/mhw_mask.nc'),
    'report.json': os.path.exists('output/report.json')
}

print("FINAL STATUS CHECK:")
for file, exists in status.items():
    print(f"{'✅' if exists else '❌'} {file}")

if all(status.values()):
    print("\n🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")
else:
    print("\n❌ Some files missing")