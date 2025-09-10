.PHONY: install prerequisites reset docs publish uv-sync-all docs

VERSION := $(shell git rev-parse --short HEAD)

default:
	@$(MAKE) --no-print-directory install

uv-sync-all:
	@uv sync --dev --all-groups

install:
	@if command -v uv > /dev/null; then $(MAKE) uv-sync-all; else $(MAKE) prerequisites; $(MAKE) uv-sync-all; fi

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

docs:
	@mkdocs build -c
