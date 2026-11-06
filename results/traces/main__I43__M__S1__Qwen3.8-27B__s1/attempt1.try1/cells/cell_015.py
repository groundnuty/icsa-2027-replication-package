s = open('/usr/local/lib/python3.12/site-packages/numpy/lib/_function_base_impl.py').read()
i = s.find('_QuantileMethods =')
print(s[i:i+3000])
