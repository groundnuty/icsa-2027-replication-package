import onedatarestfsspec.core as core, inspect, re
src = inspect.getsource(core)
# find the class definition of OnedataFileSystem and look at its attributes / API defaults
m = re.search(r'class OnedataFileSystem.*?(?=\nclass |\Z)', src, re.S)
cls_src = m.group(0)
print("class source length:", len(cls_src))
print(cls_src[:6000])
