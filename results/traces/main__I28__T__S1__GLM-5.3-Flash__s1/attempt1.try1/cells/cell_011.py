import os, time
# test if local disk persists across calls (write marker now, check next call)
os.makedirs('/tmp/persisttest', exist_ok=True)
with open('/tmp/persisttest/marker.txt','w') as fh:
    fh.write('hello')
print("wrote marker")
