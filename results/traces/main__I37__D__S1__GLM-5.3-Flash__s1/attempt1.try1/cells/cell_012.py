import onedatarestfsspec.core as core, inspect, re
src = inspect.getsource(core)
m = re.search(r'class OnedataFileSystem.*?(?=\nclass |\Z)', src, re.S)
cls_src = m.group(0)
# find methods mentioning 'children' or listing
idx = cls_src.find('def ls')
print(cls_src[idx-200:idx+4000])
