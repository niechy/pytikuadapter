import pkgutil
import importlib

__all__ = []

for loader, name, is_pkg in pkgutil.walk_packages(__path__):
    if name != '__init__':
        module = importlib.import_module(f'.{name}', __package__)
        globals()[name] = module
        __all__.append(name)
