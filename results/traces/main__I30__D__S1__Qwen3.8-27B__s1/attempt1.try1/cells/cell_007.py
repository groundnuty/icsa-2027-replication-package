import numpy as np
print(np.__version__)
# quick check of hazen quantile definition on small example
x = np.arange(1, 12, dtype=np.float64)
print(np.quantile(x, 0.9, method='hazen'))   # HF type 5: h=(j-0.5)/n -> index 9.5*... let's see
print(np.quantile(x, 0.9, method='linear'))
# expected hazen: positions (j-0.5)/n, p=0.9 -> (j-0.5)/11=0.9 -> j=10.4 -> between x[10]=10 and x[11]=11 -> 10.4
print("hazen expected 10.4, linear expected", 1+0.9*10)
