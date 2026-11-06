import re
s = open('/usr/local/lib/python3.12/site-packages/numpy/lib/_function_base_impl.py').read()
i = s.find('def _quantile(')
j = s.find('def _quantile_')
seg = s[i:i+6000]
k = seg.find('hazen')
print(seg[max(0,k-2500):k+1500])
