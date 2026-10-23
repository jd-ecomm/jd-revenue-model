# Daily publish runbook (Mon-Fri 9:39 Vancouver)

Source of truth: the Claude dashboard https://claude.ai/artifact/TaNmEVUHF97VSVghtB27SU ("Predictive Revenue Model").
This repo holds the locked copy (`index.html`) and an encrypted kit (`kit.tar.gz.enc`) of every input the last build used,
so each run only downloads what changed. Never commit an unencrypted file with data in it.

1. Attach and clone `jd-ecomm/jd-revenue-model` with push access.
2. Team password: Projects `project_read` of `claude/prm-site-password.md` in the "JD Sports" project (first non-empty line). Export it as `PRM_PW` for the shell only; never print it, write it to a file in the repo, or put it in a commit message. If the doc is missing, stop. To change the password, Ryan edits that doc; the next run re-locks the site with it.
3. Unpack the kit: `mkdir -p /tmp/kit && openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass env:PRM_PW -in kit.tar.gz.enc | tar -xz -C /tmp/kit`.
4. Sync the kit with the dashboard:
   - ArtifactData `list` collection `datasets` (limit 200) with `out_dir` /tmp/sync. Replace /tmp/kit/datasets with those JSON files.
   - For every dataset whose `source.kind` is `file`, take the id from `source.url` (`/_blob/<id>`). If /tmp/kit/blobs/<id>.* is missing, fetch it with Artifact `read`, `path` = <id>, `out_dir` = /tmp/kit/blobs (one id per call). Delete blobs no dataset uses, except the three fonts (872f8638673a9b30a10eb06bf31f09f2, fdebddcbf42081ff9e6cbbf305b30e2a, ba54dc9ca7f335658e80aef52c24520d).
   - ArtifactData `get` collection `files`, doc `index.html`; write its `text` field to /tmp/kit/index.html. If the page references a new `/_blob/<id>` font, fetch it the same way.
   - Lifetimely `get-metric-time-series`, timeframe day, dateFrom 2026-09-13, dateTo yesterday (Vancouver), for `product_revenue`, `total_discounts`, `refunds`. Write each `values` list as [{"date","value" (number)}] to /tmp/kit/lt/lt_sales.json, lt_discounts.json, lt_refunds.json respectively.
5. From the repo root: `tools/publish.sh /tmp/kit`. It must print "data through <yesterday>"; if not, stop and report.
6. Commit `index.html` and `kit.tar.gz.enc` ("Daily refresh YYYY-MM-DD") and push to `main`.
7. Report one line: data through date, files that changed, and the site URL https://jd-ecomm.github.io/jd-revenue-model/.

Stop without pushing if any download fails, the password is missing, or the build errors. A stale but correct site beats a broken one.
