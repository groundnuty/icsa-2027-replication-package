import subprocess,os
print(os.getcwd())
write=open('/tmp/write.py').read() if os.path.exists('/tmp/write.py') else None
print(write is None)