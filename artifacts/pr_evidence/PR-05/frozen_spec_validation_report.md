# Frozen specification validation

Create and draft-edit validate nonblank title/objective and nonempty protocol. Freeze delegates lifecycle, canonical JSON serializability, hash, and UTC timestamp behavior to the shared PR-03 helper. Non-DRAFT freeze, blank material, empty protocol, malformed canonical material, missing linked hypothesis, and cross-project hypothesis links are rejected without raw serializer/SQL errors at the application boundary.
