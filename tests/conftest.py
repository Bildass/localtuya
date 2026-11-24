"""Load the bundled pytuya package without importing Home Assistant."""
import importlib.util
import sys
from pathlib import Path

PYTUYA_DIR = Path(__file__).resolve().parent.parent / "custom_components" / "localtuya_bildass" / "pytuya"

if "pytuya" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        "pytuya", PYTUYA_DIR / "__init__.py", submodule_search_locations=[str(PYTUYA_DIR)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["pytuya"] = module
    spec.loader.exec_module(module)
