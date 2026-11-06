# Daily publish runbook (cloud task "PRM site publish (cloud)", Mon-Fri 9:40am Vancouver)

The refresh task (work PC, 9:15) updates the Claude dashboard but cannot push to GitHub: device-bound sessions have no repo access. Since 6 Nov 2026 a separate CLOUD task publishes the site at 9:40 by patching only what changed:

1. add_repo jd-ecomm/jd-revenue-model (push); clone depth 1.
2. ArtifactData `list` collection `datasets` (limit 200, NO out_dir) on https://claude.ai/artifact/TaNmEVUHF97VSVghtB27SU. Write the documents as a JSON list of {"id","data"} to /tmp/pw/datasets.json.
3. Gate: the refresh must have run today. If no dataset has `data.updated.at` on today's Vancouver date, wait 10 minutes and re-list (up to 3 times); then stop and report "refresh hasn't run".
4. For each `file` dataset whose blob id (from `source.url`) differs from tools/blob_manifest.json, Artifact `read` with `path` = <blob id>, `out_dir` = /tmp/pw/blobs (ONE id per call; `paths` with several ids fails).
5. Lifetimely get-metric-time-series, timeframe day, dateFrom 2026-09-13, dateTo yesterday: product_revenue, total_discounts, refunds -> /tmp/pw/lt/lt_sales.json, lt_discounts.json, lt_refunds.json as [{"date","value" (number)}].
6. `python3 tools/patch_site.py /tmp/pw` must print "data through <yesterday>". Commit index.html + tools/blob_manifest.json as "Daily refresh YYYY-MM-DD (booked to <last booked JESTA day>)", push to main, confirm with git log origin/main -1.

If the dashboard's PAGE changed (files/index.html or calcs.js edited), patching keeps the old page: do a full rebuild with the steps below instead.

## Full rebuild (page changes only)

Run as step 5 of the single scheduled task "PRM daily refresh + site publish", only after the dashboard refresh succeeded. There is no separate publish task.

Source of truth: the Claude dashboard https://claude.ai/artifact/TaNmEVUHF97VSVghtB27SU ("Predictive Revenue Model").
This repo holds the published copy (`index.html`). The site is not password-locked. Raw inputs (the kit) are
never committed: each run rebuilds the kit from scratch in /tmp/kit.

1. Attach and clone `jd-ecomm/jd-revenue-model` with push access.
2. Start an empty kit: `rm -rf /tmp/kit && mkdir -p /tmp/kit/datasets /tmp/kit/blobs /tmp/kit/lt`.
3. Sync the kit with the dashboard:
   - ArtifactData `list` collection `datasets` (limit 200), without `out_dir` (refused for this artifact). Write each document's `data` object to /tmp/kit/datasets/<id>.json (so `source` is at the top level).
   - For every dataset whose `source.kind` is `file`, take the id from `source.url` (`/_blob/<id>`) and fetch it with Artifact `read`, `path` = <id>, `out_dir` = /tmp/kit/blobs (one id per call). Also fetch the three fonts (872f8638673a9b30a10eb06bf31f09f2, fdebddcbf42081ff9e6cbbf305b30e2a, ba54dc9ca7f335658e80aef52c24520d).
   - ArtifactData `get` collection `files`, doc `index.html`; write its `text` field to /tmp/kit/index.html. The page loads its calculations from another page file (`<script src="calcs.js">`): for every `<script src="NAME">` in it, ArtifactData `get` collection `files`, doc `NAME`, and write its `text` field to /tmp/kit/files/NAME. build.py inlines them and stops if one is missing. If the page references another `/_blob/<id>`, fetch it the same way.
   - Lifetimely `get-metric-time-series`, timeframe day, dateFrom 2026-09-13, dateTo yesterday (Vancouver), for `product_revenue`, `total_discounts`, `refunds`. Write each `values` list as [{"date","value" (number)}] to /tmp/kit/lt/lt_sales.json, lt_discounts.json, lt_refunds.json respectively.
4. From the repo root: `tools/publish.sh /tmp/kit`. The build must print "data through <yesterday>"; if not, stop and report.
5. Commit `index.html` ("Daily refresh YYYY-MM-DD") and push to `main`. Never commit anything from /tmp/kit.
6. Report one line: data through date, files that changed, and the site URL https://jd-ecomm.github.io/jd-revenue-model/.

Stop without pushing if any download fails or the build errors. A stale but correct site beats a broken one.
