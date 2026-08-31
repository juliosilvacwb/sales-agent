import sys
import types
import importlib.util
from pathlib import Path

# Register 'auth-service' directory as 'auth_service' module in sys.modules
auth_dir = Path(__file__).resolve().parent.parent / "auth-service"
if auth_dir.exists() and "auth_service" not in sys.modules:
    auth_service_mod = types.ModuleType("auth_service")
    auth_service_mod.__path__ = [str(auth_dir)]
    sys.modules["auth_service"] = auth_service_mod
    
    app_file = auth_dir / "app.py"
    if app_file.exists():
        spec = importlib.util.spec_from_file_location("auth_service.app", app_file)
        if spec and spec.loader:
            app_mod = importlib.util.module_from_spec(spec)
            sys.modules["auth_service.app"] = app_mod
            spec.loader.exec_module(app_mod)
