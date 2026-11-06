import os
print(os.listdir('/'))
try:
    print(os.listdir('/data'))
except Exception as e:
    print("ERR", e)
