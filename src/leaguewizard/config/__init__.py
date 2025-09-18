"""Handles loading the application configuration from a 'config.toml' file.

This module searches for 'config.toml' in several predefined locations:
1. User's local appdata directory (e.g., %LOCALAPPDATA%/LeagueWizard/config.toml).
2. The directory of the executable if the application is frozen.
3. The module's own directory if running as a script.

If a configuration file is found, its contents are loaded into the `WizConfig` variable.
If no file is found, a default `WizConfig` is provided.
"""

import os
import pathlib
import sys

from leaguewizard.constants import MIN_PY_VER

if sys.version_info[1] <= MIN_PY_VER:
    from tomli import load
else:
    from tomllib import load

options = []

appdata_dir = os.getenv("LOCALAPPDATA", None)

if appdata_dir is not None:
    appdata_option = pathlib.Path(appdata_dir) / "LeagueWizard" / "config.toml"
    options.append(appdata_option)

if getattr(sys, "frozen", False):
    exe_dir_option = pathlib.Path(sys.executable).parent / "config.toml"
    options.append(exe_dir_option)
else:
    module_config_option = pathlib.Path(__file__).parent / "config.toml"
    options.append(module_config_option)

for candidate in options:
    if candidate.exists():
        path = candidate.resolve()
        break

if "path" in locals():
    with path.open(mode="rb") as f:
        WizConfig = load(f)
else:
    WizConfig = {"spells": {"flash": ""}}
