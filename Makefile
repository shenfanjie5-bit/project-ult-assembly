PYTHON ?= python3
PROFILE ?= lite-local
DRY_RUN ?=
ASSEMBLY := PYTHONPATH=src $(PYTHON) -m assembly.cli.main
DRY_RUN_FLAG := $(if $(DRY_RUN),--dry-run,)

.PHONY: list-profiles render-profile bootstrap shutdown healthcheck smoke contract-suite e2e export-registry test

list-profiles:
	$(ASSEMBLY) list-profiles

render-profile:
	$(ASSEMBLY) render-profile --profile $(PROFILE)

bootstrap:
	$(ASSEMBLY) bootstrap --profile $(PROFILE) $(DRY_RUN_FLAG)

shutdown:
	$(ASSEMBLY) shutdown --profile $(PROFILE) $(DRY_RUN_FLAG)

healthcheck:
	$(ASSEMBLY) healthcheck --profile $(PROFILE)

smoke:
	$(ASSEMBLY) smoke --profile $(PROFILE)

contract-suite:
	$(ASSEMBLY) contract-suite --profile $(PROFILE)

e2e:
	$(ASSEMBLY) e2e --profile $(PROFILE)

export-registry:
	$(ASSEMBLY) export-registry

test:
	$(PYTHON) -m pytest tests/profiles tests/registry tests/bootstrap tests/health tests/smoke tests/e2e tests/contracts tests/compat tests/cli -q
