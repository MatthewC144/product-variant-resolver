# T49.4 — Human-storage runtime packaging requirements

Date:2026-09-15. Lite. Scoped execution authorized by owner「請幫我執行下一步」after T49.4 was
explicitly identified as runtime packaging/operational closure. This is not default rollout approval.

## Observable requirements

### HSRP-R1 — Preserve the default service
WHILE the optional package is added, THE SYSTEM SHALL keep the existing Dockerfile,Compose file,`api`
image command,offline default behavior,canonical authority and public nondebug response unchanged.

### HSRP-R2 — Require explicit opt-in and an immutable profile
WHEN an operator selects the human-storage package, THE SYSTEM SHALL require a separately named
dedicated Compose file/profile/service and a regular read-only mounted profile bound to the exact image;
missing profile input SHALL fail before a healthy service is reported,with no automatic fallback.

### HSRP-R3 — Package every frozen runtime dependency and only necessary reports
WHEN the dedicated image is built, THE SYSTEM SHALL include every file named by the strict source manifest,
including the four frozen external JSON inputs and source-freeze producer,and SHALL exclude unrelated
generated reports so adding later evidence does not silently change the runtime image.

### HSRP-R4 — Retain runtime safety boundaries
WHEN the optional service runs, THE SYSTEM SHALL use one Uvicorn worker,nonroot user,read-only root
filesystem,tmpfs-only scratch and loopback-only host publication. It SHALL remain file-backed and
SHALL NOT receive a database URL,production credential,host database volume or write capability.

### HSRP-R5 — Verify observable behavior in an isolated package run
WHEN the frozen package is tested, THE SYSTEM SHALL verify healthy/versioned storage readiness,
debug-only storage evidence,four unchanged nondebug canonical responses,exact image identity and
complete cleanup of only the isolated Compose project. Raw status/checksum evidence SHALL be retained.

### HSRP-R6 — Close only the bounded packaging task
WHEN QA completes, THE SYSTEM SHALL publish review,evidence,AI rubric,runbook and narrative project log;
it SHALL NOT claim PostgreSQL rollout,production SLA,concurrency/durability,real3k scale,source rights
or color/wheel/tampo release identity.
