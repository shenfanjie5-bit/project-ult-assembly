# FrontEnd Read-Only Polish Evidence

Recorded: 2026-04-27T04:27:34Z

Scope:

- Record Project ULT FrontEnd read-only polish evidence.
- Close FE-01 through FE-03 from the stabilization master checklist.
- FrontEnd-only implementation; no backend, frontend-api, assembly runtime, or
  endpoint changes are included in the FrontEnd commit.
- No new page was added.
- No Project ULT write call, command, run, freeze, release-freeze, min-cycle,
  e2e-run, replay POST, or graph simulate surface was added.

Commit under smoke:

- FrontEnd:
  `0c8e0523c72cb13fb968faecd36398ec0211b427`
  `Stabilize Project ULT read-only routing`

FrontEnd role validation:

```text
npm run check
  passed

npm run lint
  passed

npm run build
  passed

git diff --check
  passed

forbidden diff grep:
  no new POST/PUT/PATCH/DELETE
  no command/run/freeze/release-freeze/min-cycle/e2e-run
  no replay POST
  no graph simulate
```

FrontEnd role browser smoke:

```text
/project-ult/system?data_mode=projectUlt
  normal

/project-ult/data?data_mode=projectUlt&entity_limit=9999&canonical_limit=9999&raw_limit=9999
  limits normalized to 500
  no 422

refresh:
  data_mode=projectUlt retained

Project ULT quick links:
  hrefs retain data_mode=projectUlt

/does-not-exist?data_mode=projectUlt
  redirects to System Map

risk routes:
  /admin
  /subsystems
  /audit
  /graph
  /stock/600519.SH
  all redirect to System Map in projectUlt mode

console:
  no CORS
  no 404
  no 422
  no Failed to fetch
  no unsupported legacy endpoint
```

Independent review result:

```text
FE-01 data_mode query/store synchronization: closed
FE-02 API-3A Data Explorer limit clamp: closed
FE-03 unknown route fallback: closed
```

Independent review notes:

```text
FE-01:
  URL data_mode=projectUlt syncs store/persisted mode and Project ULT mode
  restores the query parameter when missing.

  Key files:
    /Users/fanjie/Desktop/BIG/FrontEnd/src/App.tsx
    /Users/fanjie/Desktop/BIG/FrontEnd/src/utils/dataMode.ts
    /Users/fanjie/Desktop/BIG/FrontEnd/src/components/projectUlt/ProjectUltReadOnly.tsx

FE-02:
  entity/canonical/raw limits are clamped during page initialization, URL
  correction, user input, and request hook construction.
  Backend request max is 500.
  Empty, negative, zero, NaN, and over-limit values do not emit invalid backend
  queries.

  Key files:
    /Users/fanjie/Desktop/BIG/FrontEnd/src/pages/DataExplorer/index.tsx
    /Users/fanjie/Desktop/BIG/FrontEnd/src/api/projectUlt/hooks.ts

FE-03:
  Unknown routes in Project ULT mode redirect to
  /project-ult/system?data_mode=projectUlt.
  /admin, /subsystems, /audit, legacy /graph, and /stock/:id are guarded to
  System Map in Project ULT mode.

  Key file:
    /Users/fanjie/Desktop/BIG/FrontEnd/src/App.tsx
```

Independent reviewer commands:

```text
npm run check
  passed

npm run lint
  passed

npm run build
  passed

git diff --check
  passed

git diff --check \
  0c8e0523c72cb13fb968faecd36398ec0211b427^ \
  0c8e0523c72cb13fb968faecd36398ec0211b427
  passed

forbidden grep:
  no Project ULT POST/PUT/PATCH/DELETE
  no command/run/freeze/release-freeze/min-cycle/e2e-run
  no graph simulate call

Notes:
  Matches were limited to legacy admin mutation hooks, generic apiClient helper
  methods, Project ULT orchestrator/runs GET, and read-only boundary copy.
```

Independent browser limitation:

```text
The reviewer confirmed a dev server could start and that curl to the Project
ULT deep link returned 200. The in-app browser backend was unavailable and the
repo did not have Playwright installed, so the independent review used code-
level route/hook review plus the FrontEnd role's browser smoke evidence above.
```

Working tree boundary:

```text
FrontEnd HEAD:
  0c8e0523c72cb13fb968faecd36398ec0211b427

FrontEnd origin/main:
  0c8e0523c72cb13fb968faecd36398ec0211b427

Remaining local modified files:
  README.md
  src/mocks/data/projectUltData.ts

Interpretation:
  These local diffs predated the FrontEnd polish task and were not part of
  commit 0c8e0523. They were not modified, reverted, staged, committed, or
  pushed by the independent reviewer.
```

Boundary:

- No backend or frontend-api code was changed by this evidence step.
- No assembly matrix, registry, or release docs are promoted by this evidence.
- This evidence does not promote `frontend-api` into verified compatibility
  matrix rows.
