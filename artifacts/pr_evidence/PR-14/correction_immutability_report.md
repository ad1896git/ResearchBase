# Correction immutability report

CorrectionRecord is append-only; direct UPDATE is rejected. Creation leaves target rows, target hashes, and exact provenance edges unchanged. Multiple corrections to one exact target are allowed and ordered by created_at/id. Projection exposes correction IDs. Fresh evidence correction ID: `01a05810-3307-70d5-bdac-2b4a92980801`.
