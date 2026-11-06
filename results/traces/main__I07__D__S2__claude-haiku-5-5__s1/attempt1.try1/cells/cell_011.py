
import subprocess, os
print(os.getcwd())
code3 = open('/work/s3.py').read() if os.path.exists('/work/s3.py') else None
print(code3 is not None)
