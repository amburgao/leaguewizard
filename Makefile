# -*- MakeFile -*-
# ==============================================================================
#                             Project Variables
# ==============================================================================

# Load environment variables from .env file
-include .env

# Project settings
PROJECT_NAME := leaguewizard
VERSION      := $(shell uv version --short 2>/dev/null || echo "0.0.0")
EXE_OUT      := $(PROJECT_NAME)-$(VERSION).exe
TARGET       ?= None

# Shell settings
SHELL := /bin/bash

# ==============================================================================
#                              Default Target
# ==============================================================================

.DEFAULT_GOAL := help

# ==============================================================================
#                             User-Facing Targets
# ==============================================================================

.PHONY: help install lint clean test docs push-docs wheel pypi exe release bump reset-hard clean-deploys

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Available targets:"
	@echo "  install        Install all development dependencies."
	@echo "  lint           Run linters and formatters."
	@echo "  clean          Remove build artifacts and temporary files."
	@echo "  test           Run tests (not yet implemented)."
	@echo "  docs           Build the documentation."
	@echo "  push-docs      Build and push documentation to gh-pages."
	@echo "  wheel          Build the Python wheel."
	@echo "  pypi           Publish the wheel to PyPI."
	@echo "  exe            Build the application executable."
	@echo "  release        Create a new GitHub release from the current version."
	@echo "  bump           Bump the project version (e.g., 'make bump TARGET=minor')."
	@echo "  reset-hard     Reset the repository to a clean state (discards all changes)."
	@echo "  clean-deploys  Clean old deployments."

install: uv-sync-dev
	@echo -e "\u2705 Development environment is ready."

lint: uv-sync-dev
	@echo -e "\u23F3 Running linters..."
	@uv run -q pyproject-fmt pyproject.toml >/dev/null
	@echo -e "\u2705 pyproject-fmt check passed."
	@uv run -q ruff check src/leaguewizard >/dev/null
	@echo -e "\u2705 ruff check passed."
	@uv run -q ruff format src/leaguewizard >/dev/null
	@echo -e "\u2705 ruff format complete."
	@uv run -q codespell -f src/leaguewizard >/dev/null
	@echo -e "\u2705 codespell passed."
	@echo -e "\u2705 Linting complete."

clean:
	@echo "Cleaning up build artifacts and temporary files..."
	@rm -rf build/ dist/ *.spec .venv/ .pytest_cache/ .ruff_cache/
	@find . -type f -name "*.py[co]" -delete
	@find . -type d -name "__pycache__" -delete
	@echo -e "\u2705 Cleanup complete."

test:
	@echo "Tests are not implemented yet."

# ==============================================================================
#                         Dependency Management
# ==============================================================================

.PHONY: uv-sync-lint uv-sync-dev uv-sync-docs uv-sync-all prerequisites

uv-sync-dev: prerequisites
	@echo "Syncing development dependencies..."
	@uv sync --dev --group types -q
	@echo -e "\u2705 Development dependencies synced."

uv-sync-docs: prerequisites
	@echo "Syncing documentation dependencies..."
	@uv sync --group docs -q
	@echo -e "\u2705 Documentation dependencies synced."

uv-sync-all: prerequisites
	@echo "Syncing all dependencies..."
	@uv sync --dev --all-groups -q
	@echo -e "\u2705 All dependencies synced."

prerequisites:
	@pipx list --short | grep -q "uv" || pipx install --force uv
	@pipx list --short | grep -q "mbake" || pipx install --force mbake
	@pipx list --short | grep -q "check-jsonschema" || pipx install --force check-jsonschema
	@pipx list --short | grep -q "codespell" || pipx install --force codespell[toml]
	@pipx list --short | grep -q "pre-commit" || pipx install --force pre-commit
	@pipx list --short | grep -q "pyproject-fmt" || pipx install --force pyproject-fmt
	@pipx list --short | grep -q "ruff" || pipx install --force ruff
	@pipx list --short | grep -q "watchfiles" || pipx install --force watchfiles

# ==============================================================================
#                         Build and Release Targets
# ==============================================================================

wheel:
	@echo "Building wheel..."
	@uv build
	@echo -e "\u2705 Wheel built successfully."

pypi: wheel
	@echo "Publishing to PyPI..."
	@uv publish
	@echo -e "\u2705 Published to PyPI."

exe: lint
	@echo -e "\u23F3 Building executable..."
	@rm -rf build dist *.spec >/dev/null 2>&1
	@uvx -p 3.10 --from pip-tools pip-compile ./pyproject.toml >/dev/null 2>&1
	@uvx --with-requirements ./requirements.txt -p 3.10 pyinstaller \
		--name "$(EXE_OUT)" \
		--noconsole \
		--onefile \
		--optimize 2 \
		--icon "./.github/images/logo.ico" \
		--clean \
		--upx-dir "$(UPX_DIR)" \
		--add-data "src/leaguewizard/data/images:leaguewizard/data/images" \
		--add-data "src/leaguewizard/data/certs:leaguewizard/data/certs" \
		--log-level ERROR \
		--paths src/leaguewizard \
		./src/leaguewizard/__main__.py &> /dev/null
	@echo -e "\u2705 Executable created at ./dist/$(EXE_OUT)"

release: exe
	@echo "Creating GitHub release v$(VERSION)..."
	@gh release create v$(VERSION) ./dist/$(EXE_OUT) --latest --notes-from-tag -t v$(VERSION)
	@echo -e "\u2705 GitHub release created."

# ==============================================================================
#                         Documentation Targets
# ==============================================================================

docs: uv-sync-docs
	@echo "Building documentation..."
	@PRE_COMMIT_ALLOW_NO_CONFIG=1 git worktree add ../gh-pages gh-pages -f
	@(. .venv/bin/activate; mkdocs build -c -d ../gh-pages)
	@echo -e "\u2705 Documentation built."

push-docs: docs
	@echo "Pushing documentation to gh-pages..."
	@(cd ../gh-pages && \
	git add -A && \
	git commit --amend --no-edit && \
	git push origin gh-pages --no-verify -f && \
	cd ../leaguewizard && \
	rm -rf ../gh-pages)
	@echo -e "\u2705 Documentation pushed."

# ==============================================================================
#                               Git Utilities
# ==============================================================================

reset-hard:
	@echo -n "⚠️ This will discard all uncommitted changes. Are you sure? [y/N] " && read answer && [ "$${answer:-N}" = "y" ] || (echo "Operation cancelled." && exit 1)
	@echo "Resetting repository..."
	@git reset --hard HEAD
	@git clean -fdX
	@echo -e "\u2705 Repository reset to a clean state."

clean-deploys:
	@if [ "$(GIT_USERNAME)" = "NOT_SET" ] || [ "$(PROJECT_NAME)" = "NOT_SET" ] || [ "$(TARGET_BRANCH)" = "NOT_SET" ]; then \
		echo "Error: GIT_USERNAME, PROJECT_NAME, and TARGET_BRANCH must be set in your environment or .env file."; \
		exit 1; \
	fi
	@echo "Cleaning old deployments..."
	@pwsh.exe -File ./scripts/clean_deployments.ps1
	@echo -e "\u2705 Deployments cleaned."

bump:
	@if [ "$(TARGET)" = "None" ]; then \
		echo "Error: No bump target specified. Use 'make bump TARGET=<target>', where target is one of: major, minor, patch."; \
		exit 1; \
	fi
	@echo "Bumping version with target: $(TARGET)..."
	@uv version --bump $(TARGET)
	@git add pyproject.toml
	@echo -e "\u2705 Version bumped. Don't forget to commit the change."
