# PR-14R7 protocol correction

PR-14R7 adopts `evidence_protocol = non-self-referential-v1`.

A Git commit cannot be required to contain its own SHA in a tracked payload:
changing the payload changes the tree and therefore changes the containing
commit SHA. The former self-referential acceptance requirement is removed.

Committed evidence records the immutable subject and known evidence parent.
The independent reviewer resolves the containing evidence commit directly
from Git. Its omission from this payload is intentional and complete.

`self_commit_sha_in_payload = false`
