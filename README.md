<p align="center">
  <a href="" rel="noopener">
 <img width=256px height=256px src="https://raw.githubusercontent.com/amburgao/leaguewizard/86de1360c231a01b89cb0f86b7cb9a6df155a89e/.github/images/logo.png" alt="Project logo"></a>
</p>

# Table of contents

1. [Introduction](#introduction)
2. [Features](#features)
3. [Installation](#installation)
    1. [Github Releases](#github-releases)
    1. [pipx](#pipx)
4. [Development](#development)
5. [Documentation](#documentation)
6. [License](#license)

# Introduction

Auto sync your itemsets, perks and spells with mobalytics.gg ones on champion selection.

## Features

- No user interaction needed except for selecting your champion
- Import latest itemsets (champion build)
- Import latest perks (champion runes)
- Import latest summoner spells

## Installation

### Github-Releases

Go to the latest [LeagueWizard Release](https://github.com/amburgao/leaguewizard/releases/latest) and download the standalone binary.

### pipx

Install LeagueWizard using pipx

~~~pwsh
pipx install leaguewizard
~~~

Then run with

~~~pwsh
leaguewizard.exe
~~~

## Development

Prerequisites

~~~pwsh
pipx install uv
~~~

Clone the repository

~~~pwsh
git clone https://github.com/amburgao/leaguewizard.git

cd leaguewizard
~~~

Install the project with dev and optional dependencies

~~~pwsh
uv sync --dev --all-groups
~~~

Then just activate the environment

~~~pwsh
./.venv/Scripts/activate
~~~

*ps: you can use Make to setup the project, simple as:*

~~~pwsh
cd leaguewizard

make

./.venv/scripts/activate
~~~

## Documentation

[Documentation](https://amburgao.github.io/leaguewizard/)

## License

[MIT](./LICENSE)
