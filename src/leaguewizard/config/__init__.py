import os
import pathlib
import sys

import tomllib

options = []

appdata_dir = os.getenv("LOCALAPPDATA")

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
        WizConfig = tomllib.load(f)
else:
    WizConfig = {}
