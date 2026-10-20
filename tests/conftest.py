"""Load integration modules without requiring a Home Assistant installation."""

import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).parents[1]
CUSTOM_COMPONENTS = ROOT / "custom_components"
DOMAIN_PACKAGE = CUSTOM_COMPONENTS / "kryptex_pool"

custom_components = ModuleType("custom_components")
custom_components.__path__ = [str(CUSTOM_COMPONENTS)]
sys.modules.setdefault("custom_components", custom_components)

domain = ModuleType("custom_components.kryptex_pool")
domain.__path__ = [str(DOMAIN_PACKAGE)]
sys.modules.setdefault("custom_components.kryptex_pool", domain)
