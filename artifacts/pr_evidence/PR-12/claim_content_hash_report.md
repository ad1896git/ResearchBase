# Claim content hash report

ClaimVersion material is exactly `statement`, `scope`, `qualification`, and `support_set_hash`; the content hash is calculated over that material with the existing canonical JSON policy. An independent test oracle verified key-order equivalence, single-variable sensitivity for every material field, and exclusion of lifecycle/identity metadata.

Unserializable scope is translated to the stable `VALIDATION_ERROR` application error rather than a raw serializer or driver exception. The content-hash tests also prove that changing support_set_hash changes content_hash.
