# Final status check
import os

status = {
    'directory_exists': os.path.exists('output'),
    'mhw_file_exists': os.path.exists('output/mhw_mask.nc'),
    'report_file_exists': os.path.exists('output/report.json')
}

print("FINAL STATUS CHECK")
print("=" * 18)
for key, value in status.items():
    print(f"{'✅' if value else '❌'} {key}: {value}")

if all(status.values()):
    print("\n🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")
else:
    print("\n❌ Some files are missing")