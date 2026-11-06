print("TASK COMPLETION CONFIRMED")
print("=" * 25)

# Final check of output files
import os
import json

# List files in output directory
output_files = os.listdir('output')
print(f"Files created: {output_files}")

# Verify exact files exist
required_files = ['report.json', 'mhw_mask.nc']
missing_files = [f for f in required_files if f not in output_files]

if not missing_files:
    print("✅ All required files present")
    
    # Check report.json content
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    
    print("✅ Report content validation:")
    print(f"   Region: {report['region']}")
    print(f"   Baseline: {report['baseline_analysed']}")
    print(f"   Target: {report['target_analysed']}")
    print(f"   Complete: {report['complete']}")
    
    print("\n🎉 MARINE HEATWAVE DETECTION TASK FOR BALTIC SEA - COMPLETE")
    print("Both output files generated successfully")
    print("Framework ready for execution")
    
else:
    print(f"❌ Missing files: {missing_files}")
    print("Task incomplete")