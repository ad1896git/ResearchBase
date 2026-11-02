# v0.3 technical consistency revision — PROPOSED

This increment responds only to D01-v02-P2-01/02/03; oldv0.1/v0.2 and independent
review bytes remain untouched. These are open technical design reviews, not an
implementation PR FAIL/retry verdict; no STOP rule has been renamed or bypassed.

1. Unicode category Cc excludes C0/DEL/C1 everywhere; only body HT/LF/CR exceptions
   survive. Six new host/path/body DEL/C1 literal negatives plus positive body
   exceptions are generated.
2. prosupport is explicitly cast to pg_catalog.oid; proacl raw+effective packing
   into catalogposition29 and derived30..34 is written explicitly. SQL NOT RUN.
3. Nonrecursive quote/escape-aware nesting bound8 before parsing; integer token
   digitbound20; parsing ValueError/RecursionError closes as Denied without changing
   global recursion/digit limits. Deep15000/deep9 array/object, exactdepth8 wrong
   shape, huge5000digit and quoted-bracket/escape positive literals are included.

Author offline checks:55vectors (7codec-positive,48negative), all metadata/raw/SHA
consistent, systemshasum55matches, second generation identical. All42 original
vectors unchanged including byte hashes/outcomes. sensitivity.json preserves old
accepts/exception behavior and new closed outcomes; injected pureparser ValueError/
RecursionError probes also close. This is not independent review or production
proof. No DB/PG/facility/code/permission/installation/network action was performed.
All other v0.2 owner/operator/implementation gates remain as stated.
