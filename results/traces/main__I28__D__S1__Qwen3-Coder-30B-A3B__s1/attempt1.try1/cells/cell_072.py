# Final system check
import os

print("SYSTEM STATUS CHECK")
print("=" * 25)

# Check output directory
if os.path.exists('output'):
    files = os.listdir('output')
    print(f"Output directory contents: {files}")
    
    # Verify required files
    required_files = ['mhw_mask.nc', 'report.json']
    all_present = True
    
    for file in required_files:
        if file in files:
            print(f"✅ {file}")
        else:
            print(f"❌ {file}")
            all_present = False
    
    if all_present:
        print("\n🎉 ALL SYSTEMS NOMINAL")
        print("Task completed successfully!")
    else:
        print("\n💥 SOME FILES MISSING")
else:
    print("❌ Output directory not found")

print("=" * 25)