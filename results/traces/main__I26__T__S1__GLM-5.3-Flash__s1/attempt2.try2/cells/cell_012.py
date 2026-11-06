import os, json
# persistence check across calls
p='cache/persist.txt'
print('cwd', os.getcwd())
print('persist:', open(p).read() if os.path.exists(p) else 'MISSING')
print('cache dir listing', os.listdir('cache') if os.path.exists('cache') else 'no cache dir')
