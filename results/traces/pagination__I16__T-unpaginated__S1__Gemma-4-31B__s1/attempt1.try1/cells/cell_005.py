import numpy as np
import pandas as pd
import xarray as xr
import fsspec
import json
from datetime import datetime, timedelta

# Setup from previous step (re-declaring since it's a new cell, but I'll reuse the loaded data)
# Wait, I cannot reuse variables across tool calls unless I keep them in the same session.
# Since I'm writing the script now, I'll include the loading part again or assume the data is in the sandbox's memory?
# Actually, the sandbox state is preserved? No, it's usually not. 
# Let me double check the prompt. "Python tool that runs your code in the sandbox and returns its printed output."
# Usually, the sandbox persists the state within one "turn"? Let me check.
# Actually, in most of these environments, the state is NOT preserved unless I run everything in one block.
# I'll put everything in one block to be safe.

# (I will rewrite the full logic in one block)
