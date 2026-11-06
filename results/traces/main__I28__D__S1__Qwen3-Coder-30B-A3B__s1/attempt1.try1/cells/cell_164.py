# Final system check
import os

print("SYSTEM STATUS CHECK")
print("=" * 25)

# Check output directory
if os.path.exists('output'):
    files = os.listdir('output')
    print(f"Files in output: {files}")
    
    # Verify required files
    required = ['mhw_mask.nc', 'report.json']
    all_present = True
    
    for req in required:
        if req in files:
            print(f"✅ {req}")
        else:
            print(f"❌ {req}")
            all_present = False
    
    if all_present:
        print("\n🎉 ALL SYSTEMS NOMINAL")
        print("Task completed successfully!")
    else:
        print("\n💥 SOME FILES MISSING")
else:
    print("❌ Output directory not found")

print("=" * 25)