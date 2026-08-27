# Hypothesis link report (reconciled by PR-05R)

AD-PR05-001 resolves the prior ambiguity: `hypothesis_id` is identity-level, immutable after create in Phase 1, and not part of the six-field version material payload or hash. Create/freeze require existence and same project; a frozen HypothesisVersion is not required. Revisions and freeze preserve the link, and no supported Application or Repository relink operation exists.
