
import os
os.makedirs('/tmp/mhw', exist_ok=True)
with open('/tmp/mhw/persist_test.txt','w') as f:
    f.write("hello")
print("written:", os.listdir('/tmp/mhw'))
