import sys, pathlib
backend_path = pathlib.Path(__file__).resolve().parent / "synthtrade" / "backend" / "app"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
