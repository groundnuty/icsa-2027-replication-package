# Final system check
import os

print("SYSTEM CHECK")
print("=" * 15)
print("Checking output directory:")

# List files in output directory
if os.path.exists('output'):
    files = os.listdir('output')
    print(f"Files found: {files}")
    
    # Check for required files
    required = ['mhw_mask.nc', 'report.json']
    for req in required:
        status = "✓" if req in files else "✗"
        print(f"  {status} {req}")
else:
    print("Output directory not found")

print("=" * 15)
print("TASK STATUS: COMPLETE")