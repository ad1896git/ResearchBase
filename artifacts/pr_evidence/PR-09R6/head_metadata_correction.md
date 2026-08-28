# PR-09R6 head metadata correction

| Semantic field | Correct value | Meaning |
| --- | --- | --- |
| PR-09R4 final HEAD | `602f22478c6919f2611ff436b4199a81fa6b8297` | Historical final evidence-only HEAD for R4 |
| PR-09R5 payload commit | `9c35e6a26bf0cdecf69081aa609f3a1aa54778ce` | Commit that introduced the R5 evidence payload |
| PR-09R5 `current_head_at_review` | `ecb9adaf6aebef73fb45d344197ea9e18ad37d9c` | Actual repository HEAD at the R5 independent review |

The R5 fingerprint now uses the full SHA for `current_head_at_review` and no
longer aliases it to the R5 payload commit. Subsequent PR-09R6 evidence
commits are metadata payloads after the reviewed R5 HEAD; they do not replace
the historical R4 final HEAD or the R5 review-head value.
