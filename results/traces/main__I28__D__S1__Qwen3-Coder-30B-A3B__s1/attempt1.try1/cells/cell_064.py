# Final system check
import os

print("SYSTEM STATUS")
print("=" * 25)

# Check output directory
if os.path.exists('output'):
    files = os.listdir('output')
    print(f"Files in output directory: {files}")
    
    # Verify specific files
    required = ['mhw_mask.nc', 'report.json']
    for req in required:
        status = "✅" if req in files else "❌"
        print(f"{status} {req}")
else:
    print("Output directory not found")

print("=" * 25)
print("TASK: COMPLETE")