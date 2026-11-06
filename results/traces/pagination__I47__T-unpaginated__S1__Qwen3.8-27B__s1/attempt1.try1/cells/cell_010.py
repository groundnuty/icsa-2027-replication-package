
import os
print("cwd:", os.getcwd())
print("persistent var check:", globals().get('PERSIST_TEST'))
os.environ['PERSIST_TEST'] = 'x'
print(os.listdir('.'))
print(os.path.exists('output'))
