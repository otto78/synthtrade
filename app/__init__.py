import pathlib, sys
# Make this top‑level ``app`` package a namespace that also points to the real backend code.
_backend_path = pathlib.Path(__file__).resolve().parent.parent / "synthtrade" / "backend" / "app"
if _backend_path.is_dir():
    # Ensure the directory is on sys.path for any legacy imports.
    if str(_backend_path) not in sys.path:
        sys.path.insert(0, str(_backend_path))
    # Extend the package's __path__ so submodules (e.g. app.main) are found.
    __path__.append(str(_backend_path))
