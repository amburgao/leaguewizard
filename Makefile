
-include .env

VERSION := $(shell uv version --short)
EXE_OUT := leaguewizard-$(VERSION).exe
TARGET ?= "None"

.PHONY: bump default docs exe gh-release install make-requirements prerequisites push-docs pypi reset uv-sync-all wheel

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

push-docs:
	@. .venv/Scripts/activate; \
	$(MAKE) docs
	find ../gh-pages -mindepth 1 -not -name '.git' -exec rm -rf {} +; \
	cp -rf site/* ../gh-pages; \
	cd ../gh-pages; \
	git add .; \
	git commit -m "Update docs from main"; \
	git push origin gh-pages --no-verify -f; \
	cd ../leaguewizard

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
	@gh release create v$(VERSION) .\dist\$(EXE_OUT) --latest --notes-from-tag -t v$(VERSION)
