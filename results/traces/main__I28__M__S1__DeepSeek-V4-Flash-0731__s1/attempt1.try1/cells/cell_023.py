
import os
# Test file persistence
os.makedirs('output', exist_ok=True)
with open('/tmp/test_persistence.txt', 'w') as f:
    f.write('test')
print("wrote to /tmp")
print("Current dir:", os.getcwd())
print("Files in current dir:", os.listdir('.'))
# Check if output dir is writable
os.makedirs('output', exist_ok=True)
print("Output dir exists")
