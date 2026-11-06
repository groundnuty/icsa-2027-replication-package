
import os
# Check if the file persisted from previous call
print("Test file exists:", os.path.exists('/tmp/test_persistence.txt'))
if os.path.exists('/tmp/test_persistence.txt'):
    with open('/tmp/test_persistence.txt') as f:
        print("Content:", f.read())
print("Files in /work:", os.listdir('/work'))
