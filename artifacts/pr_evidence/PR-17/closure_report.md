# Closure Report

Positive closure passed for both the original Run and ClaimVersion. The positive Claim closure traverses direct
Measurement evidence and every StatisticalResult input.

Controlled negative cases use the accepted closure validator with missing Run and ClaimVersion references. They
produce deterministic `NOT_FOUND` diagnostics, zero visited objects, exact object type, exact path, and stable
ordering across repeated evaluation. No raw persistence exception is exposed.

The full repository PR-12 closure regression also passed in the explicit PR-09..16 baseline bundle.
