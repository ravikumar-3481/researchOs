import os
from glob import glob


__all__ = []


__init__files = glob("*.py")

for f in __init__files:
    if f.startswith("__") and f.endswith("__"):
        continue
    __all__.append(f.replace(".py", ""))