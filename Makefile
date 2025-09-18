
-include .env

VERSION := $(shell uv version --short)
EXE_OUT := leaguewizard-$(VERSION).exe
TARGET ?= "None"

.PHONY: bump default docs exe gh-release install make-requirements prerequisites push-docs pypi reset uv-sync-all uv-sync-docs wheel

default:
	@$(MAKE) --no-print-directory install

uv-sync-dev:
	@uv sync --dev --group types

uv-sync-docs:
	@uv sync --group docs

uv-sync-all:
	@uv sync --dev --all-groups

install:
	@if command -v uv > /dev/null; then $(MAKE) uv-sync-dev; else $(MAKE) prerequisites; $(MAKE) uv-sync-dev; fi

prerequisites:
	@if [ -d .venv ]; then \
		echo "🧹 Removing existing .venv..."; \
		rm -rf .venv || echo "⚠️ Failed to remove .venv, is it still activated?"; \
	fi

	@if command -v pipx > /dev/null; then \
		pipx install uv; \
	else \
		python -m pip install pipx; \
		pipx install uv; \
	fi

reset:
	@git reset --hard HEAD
	@git clean -fd

docs: uv-sync-docs
	@PRE_COMMIT_ALLOW_NO_CONFIG=1 git worktree add ../gh-pages gh-pages -f
	@mkdocs build -c -d ../gh-pages

push-docs: docs
	@(cd ../gh-pages && \
	git add -A && \
	git commit --amend --no-edit && \
	git push origin gh-pages --no-verify -f)
	@cd ../leaguewizard
	@rm -rf ../gh-pages

clean-deploys:
	@pwsh.exe -File ./scripts/clean_deployments.ps1

bump:
	@if [ "$(TARGET)" = "None" ]; then \
		"No target specified."; \
	else \
		uv version --bump $(TARGET); \
		git add pyproject.toml; \
	fi

wheel:
	@uv build

pypi: wheel
	@uv publish

make-requirements:
	@uvx -p 3.10 --from pip-tools pip-compile ./pyproject.toml --output-file requirements.txt --no-header --no-annotate --strip-extras

exe: make-requirements
	@uvx --with-requirements ./requirements.txt -p 3.10 pyinstaller -n $(EXE_OUT) --noconsole --onefile --optimize 2 ./src/leaguewizard/__init__.py --icon ./.github/images/logo.ico --clean --upx-dir $(UPX_DIR)

gh-release: exe
	@gh release create v$(VERSION) ./dist/$(EXE_OUT) --latest --notes-from-tag -t v$(VERSION)
