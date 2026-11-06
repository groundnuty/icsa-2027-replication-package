# One final check to ensure all is well
import os

# List all files in output directory
output_dir = 'output'
if os.path.exists(output_dir):
    files = os.listdir(output_dir)
    print(f"Files in output directory: {files}")
    
    # Check specifically for our required files
    required = ['mhw_mask.nc', 'report.json']
    for req in required:
        if req in files:
            print(f"✅ {req} - PRESENT")
        else:
            print(f"❌ {req} - MISSING")
else:
    print("❌ Output directory does not exist")

print("\n🎉 MARINE HEATWAVE DETECTION TASK COMPLETE")