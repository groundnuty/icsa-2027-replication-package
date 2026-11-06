import numpy as np
print(np.quantile.__module__, np.quantile.__doc__[:300])
import numpy._core
print([n for n in dir(np._core) if 'method' in n.lower()])
import numpy._core._methods as M
print([n for n in dir(M) if not n.startswith('__')])
