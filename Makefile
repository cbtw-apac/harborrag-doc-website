# Developer entry points. CI calls the underlying commands directly
# (see .github/workflows/), so nothing here is required for a green build.
#
# Windows: needs GNU Make plus a POSIX shell on PATH.
#   winget install ezwinports.make
#   add "C:\Program Files\Git\bin" to PATH   (gives make an sh.exe for recipes)

# GNU Make on Windows silently falls back to cmd.exe when sh.exe is not on PATH.
# Every recipe here is POSIX, so pin the shell rather than fail cryptically.
ifeq ($(OS), Windows_NT)
  SHELL := sh.exe
  .SHELLFLAGS := -c
endif

HARBORRAG ?= ../HarborRAG
INGEST    := scripts/ingest
SITE      := website

.DEFAULT_GOAL := help
.PHONY: help dev build typecheck check sync-local sync-stable clean

help:  ## show this help
	@grep -hE '^[a-z-]+:.*?##' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

dev:  ## serve the site with hot reload
	cd $(SITE) && pnpm start

build:  ## production build (strict: broken links and anchors throw)
	cd $(SITE) && pnpm build

typecheck:  ## tsc over the site
	cd $(SITE) && pnpm typecheck

check:  ## what CI runs: ingest tests + lint, then typecheck + strict build
	@if [ -d $(INGEST) ]; then \
	  cd $(INGEST) && uv run pytest && uv run ruff check . ; \
	else \
	  echo "skipping $(INGEST) - does not exist until Phase 2" ; \
	fi
	cd $(SITE) && pnpm typecheck && pnpm build

sync-local:  ## ingest HarborRAG main into website/docs (Next)
	cd $(INGEST) && uv run ingest.py \
	  --source $(abspath $(HARBORRAG)) --site ../../$(SITE) --channel main \
	  --source-ref local --source-sha $$(git -C $(abspath $(HARBORRAG)) rev-parse HEAD)

sync-stable:  ## ingest a release tag into a versioned snapshot; needs TAG=
	@test -n "$(TAG)" || { echo "TAG is required, e.g. make sync-stable TAG=harborrag-v2.0.0"; exit 1; }
	cd $(INGEST) && uv run ingest.py \
	  --source $(abspath $(HARBORRAG)) --site ../../$(SITE) --channel stable \
	  --source-ref refs/tags/$(TAG) --source-sha $$(git -C $(abspath $(HARBORRAG)) rev-parse $(TAG))

clean:  ## remove build output and caches
	rm -rf $(SITE)/build $(SITE)/.docusaurus
	rm -rf $(INGEST)/.pytest_cache $(INGEST)/.ruff_cache
