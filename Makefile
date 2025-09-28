
-include .env

VERSION := $$(uv version --short 2>/dev/null || echo "0.0.0")
EXE_OUT := leaguewizard-$(VERSION).exe
TARGET ?= "None"
CLEAN_EMO = "\U0001F9FC" "\U0001F9F9" "\U0001F5D1" "\U0001F9FA"

GIT_USERNAME ?= "NOT_SET"
PROJECT_NAME ?= "NOT_SET"
TARGET_BRANCH ?= "NOT_SET"

.PHONY: bump clean-deploys default docs exe gh-release install make-requirements prerequisites push-docs pypi reset uv-sync-all uv-sync-dev uv-sync-docs wheel

default:
	@$(MAKE) --no-print-directory uv-sync-dev

clean:
	@echo -n "Are you sure? [y/N] " && read and && [ "$${and:-N}" = "y" ] || (echo "Operation cancelled." && exit 1) && \
	git clean -fd && \
	git reset --hard

lint: uv-sync-lint
	@uv lock --check
	@uv run pyproject-fmt pyproject.toml
	@uv run ruff check
	@uv run codespell -f

uv-sync-lint:
	@uv sync --group types --group lint --dev

uv-sync-dev: prerequisites
	@echo "Syncing development packages..."
	@uv sync --dev --group types 2>makefile_errors.txt >/dev/null
	@echo "Done!"

uv-sync-docs:
	@uv sync --group docs

uv-sync-all:
	@uv sync --dev --all-groups

prerequisites:
	@echo "Checking prerequisites..."
	@command -v uve || $(error uv not installed.)"
reset:
	@ \
	  EMO=$$(shuf -e $(EMOJIS)); \
    set -- $$EMO; \
    echo -e "$$1 Wiping off the junk..."; \
	  git reset --hard HEAD 2>makefile_errors.txt >/dev/null; \
    echo -e "$$2 Organizing some folders..."; \
	  git clean -fd 2>makefile_errors.txt >/dev/null; \
    echo -e "\u2705 Done! Now everything is in place."

docs: uv-sync-docs
	@PRE_COMMIT_ALLOW_NO_CONFIG=1 git worktree add ../gh-pages gh-pages -f
	@(. .venv/Scripts/activate; \
  mkdocs build -c -d ../gh-pages)

push-docs: docs
	@(cd ../gh-pages && \
	git add -A && \
	git commit --amend --no-edit && \
	git push origin gh-pages --no-verify -f && \
	cd ../leaguewizard && \
	rm -rf ../gh-pages)

# This can be set on system environment ($env:) or .env files
clean-deploys:
	@if [  "$(GIT_USERNAME)" != "NOT_SET" ] && \
		[  "$(PROJECT_NAME)" != "NOT_SET" ] && \
		[  "$(TARGET_BRANCH)" != "NOT_SET" ]; then \
		pwsh.exe -File ./scripts/clean_deployments.ps1
		echo "nothing NOT_SET"; \
else \
	echo "There are required variables not set."; \
	fi

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