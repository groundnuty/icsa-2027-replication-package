import inspect
import onedatarestfsspec.core as core
src = inspect.getsource(core)
# find _split_onedata_path and space id handling
for name in ['_split_onedata_path', '_get_space_id', 'SPACE']:
    i = 0
    while True:
        i = src.find('def ' + name, i)
        if i == -1: break
        print(src[i:i+1200])
        print('---')
        i += 1
