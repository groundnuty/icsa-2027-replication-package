import subprocess, os
print(os.getcwd())
code=open('/tmp/mhw.py').read() if os.path.exists('/tmp/mhw.py') else None
print(code is None)