"""Handles loading the application configuration from a 'config.toml' file.

This module searches for 'config.toml' in several predefined locations:
1. User's local appdata directory (e.g., %LOCALAPPDATA%/LeagueWizard/config.toml).
2. The directory of the executable if the application is frozen.
3. The module's own directory if running as a script.

If a configuration file is found, its contents are loaded into the `WizConfig` variable.
If no file is found, a default `WizConfig` is provided.
"""

import loguru
import tomli
import tomli_w

from leaguewizard.core.constants import APP_DIR, CONFIG_FILE, DEV_CONFIG_FILE

options = [DEV_CONFIG_FILE, CONFIG_FILE]

_config_found = False
for option in options:
    if option.exists():
        with option.open("rb") as fp:
            _config = tomli.load(fp)
        _config_found = True
        break

if not _config_found:
    _config = {"config": {"flash": "f", "auto_accept": False}}
    APP_DIR.mkdir(exist_ok=True)
    with CONFIG_FILE.open("wb") as fp:
        tomli_w.dump(_config, fp)

flash = _config["config"].get("flash")
auto_accept = _config["config"].get("auto_accept")
logger = loguru.logger
logger.info(flash)
logger.info(auto_accept)
