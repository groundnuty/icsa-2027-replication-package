
import os
print("cwd:", os.getcwd(), "writable test:", os.access(os.getcwd(), os.W_OK))
try:
    open(os.getcwd()+'/wtest','w').close(); print("cwd writable"); os.remove(os.getcwd()+'/wtest')
except Exception as e: print("cwd write fail:", e)
print(open('/proc/mounts').read())
print("user:", os.environ.get('USER'), os.getuid())
print([d for d in os.listdir('/')])
