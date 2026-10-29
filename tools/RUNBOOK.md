# Daily publish runbook (Mon-Fri, Vancouver)

Source of truth: the Claude dashboard https://claude.ai/artifact/TaNmEVUHF97VSVghtB27SU ("Predictive Revenue Model").
This repo holds the published copy (`index.html`). The site is not password-locked. Raw inputs (the kit) are
never committed: each run rebuilds the kit from scratch in /tmp/kit.

1. Attach and clone `jd-ecomm/jd-revenue-model` with push access.
2. Start an empty kit: `rm -rf /tmp/kit && mkdir -p /tmp/kit/datasets /tmp/kit/blobs /tmp/kit/lt`.
3. Sync the kit with the dashboard:
   - ArtifactData `list` collection `datasets` (limit 200) with `out_dir` /tmp/sync. Copy those JSON files into /tmp/kit/datasets.
   - For every dataset whose `source.kind` is `file`, take the id from `source.url` (`/_blob/<id>`) and fetch it with Artifact `read`, `path` = <id>, `out_dir` = /tmp/kit/blobs (one id per call). Also fetch the three fonts (872f8638673a9b30a10eb06bf31f09f2, fdebddcbf42081ff9e6cbbf305b30e2a, ba54dc9ca7f335658e80aef52c24520d).
   - ArtifactData `get` collection `files`, doc `index.html`; write its `text` field to /tmp/kit/index.html. If the page references another `/_blob/<id>`, fetch it the same way.
   - Lifetimely `get-metric-time-series`, timeframe day, dateFrom 2026-09-13, dateTo yesterday (Vancouver), for `product_revenue`, `total_discounts`, `refunds`. Write each `values` list as [{"date","value" (number)}] to /tmp/kit/lt/lt_sales.json, lt_discounts.json, lt_refunds.json respectively.
4. From the repo root: `tools/publish.sh /tmp/kit`. The build must print "data through <yesterday>"; if not, stop and report.
5. Commit `index.html` ("Daily refresh YYYY-MM-DD") and push to `main`. Never commit anything from /tmp/kit.
6. Report one line: data through date, files that changed, and the site URL https://jd-ecomm.github.io/jd-revenue-model/.

Stop without pushing if any download fails or the build errors. A stale but correct site beats a broken one.
