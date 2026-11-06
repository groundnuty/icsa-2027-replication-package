import re
s = open('/usr/local/lib/python3.12/site-packages/numpy/lib/_function_base_impl.py').read()
i = s.find('def _quantile(')
seg = s[i:i+9000]
k = seg.find('method_p')
print(seg[k:k+3200])
