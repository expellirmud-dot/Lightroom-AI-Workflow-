# Quality Verdict Mapping

The current JSON schema uses `quality_verdict`, not a separate action field.

- `KEEP` — technically safe for automated exposure processing.
- `REVIEW` — requires manual review before any exposure apply.
- `SKIP` — technically unusable or unsafe for exposure processing.

Any material highlight or shadow risk must be recorded in the corresponding
boolean risk field and prevents automatic apply. These verdicts never delete,
reject, or otherwise mutate a photograph.
