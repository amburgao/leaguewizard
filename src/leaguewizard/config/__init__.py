"""."""

import os
import pathlib
import sys

from leaguewizard.constants import MIN_PY_VER

if sys.version_info[1] <= MIN_PY_VER:
    from tomli import load  # pyright: ignore
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
