
import os
os.makedirs('/work/output', exist_ok=True)
with open('/work/marker.txt', 'w') as f:
    f.write('hello')
print("written")
