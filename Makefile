.PHONY: install prerequisites reset docs publish

VERSION := $(shell git rev-parse --short HEAD)

default:
	@$(MAKE) --no-print-directory install

install:
	@if command -v uv > /dev/null; then uv sync --dev; else $(MAKE) prerequisites; uv sync --dev; fi

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

publish:
	@uv build -o build/$(VERSION)
	@uv publish build/$(VERSION)
