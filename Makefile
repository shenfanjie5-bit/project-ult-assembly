PYTHON ?= python3
PROFILE ?= lite-local
DRY_RUN ?=
ASSEMBLY := PYTHONPATH=src $(PYTHON) -m assembly.cli.main
DRY_RUN_FLAG := $(if $(DRY_RUN),--dry-run,)

.PHONY: list-profiles render-profile bootstrap shutdown export-registry test

list-profiles:
	$(ASSEMBLY) list-profiles

render-profile:
	$(ASSEMBLY) render-profile --profile $(PROFILE)

bootstrap:
	$(ASSEMBLY) bootstrap --profile $(PROFILE) $(DRY_RUN_FLAG)

shutdown:
	$(ASSEMBLY) shutdown --profile $(PROFILE) $(DRY_RUN_FLAG)

export-registry:
	$(ASSEMBLY) export-registry

test:
	$(PYTHON) -m pytest tests/profiles tests/registry tests/bootstrap tests/cli -q
