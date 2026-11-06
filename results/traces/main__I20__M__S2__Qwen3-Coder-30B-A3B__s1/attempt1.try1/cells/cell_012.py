# Clean up temporary files if any exist
import os
import shutil

# Remove any temporary files we might have created
temp_files = ['/tmp/climatology.npy', '/tmp/threshold.npy']
for temp_file in temp_files:
    if os.path.exists(temp_file):
        os.remove(temp_file)

print("Task completed successfully. All temporary files cleaned up.")