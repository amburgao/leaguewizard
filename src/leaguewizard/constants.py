"""Defines constant values used throughout the LeagueWizard application.

This module centralizes various fixed data, such as role mappings, summoner spell
IDs, API response error codes, and minimum Python version requirements.
"""

ROLES = {
    "top": "top",
    "jungle": "jungle",
    "mid": "mid",
    "bottom": "adc",
    "utility": "support",
}

SPELLS = {
    "SummonerBarrier": "21",
    "SummonerBoost": "1",
    "SummonerCherryFlash": "2202",
    "SummonerCherryHold": "2201",
    "SummonerDot": "14",
    "SummonerExhaust": "3",
    "SummonerFlash": "4",
    "SummonerHaste": "6",
    "SummonerHeal": "7",
    "SummonerMana": "13",
    "SummonerPoroRecall ": "30",
    "SummonerPoroThrow": "31",
    "SummonerSmite": "11",
    "SummonerSnowURFSnowball_Mark": "39",
    "SummonerSnowball": "32",
    "SummonerTeleport": "12",
    "Summoner_UltBookPlaceholder": "54",
    "Summoner_UltBookSmitePlaceholder": "55",
}


RESPONSE_ERROR_CODE = 400

MIN_PY_VER = 10
