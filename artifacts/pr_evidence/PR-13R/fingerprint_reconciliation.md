# Fingerprint reconciliation

PR-12 baseline is `5b4d7e1ffa3509adbb2f324d2fb82df9883780cb`; reviewed PR-13 HEAD is
`d99c215c5d06153da334de88021393588f177a1e`; PR-13R implementation is
`6355b2f724e766b33aa7b07cdbfd965d02e449eb` plus test hardening commit
`b6afdb78a08ae29070291d73959098a9f11087a9`. Evidence payload commit is
`ad5790c26dd26ef374ac96e36eb9283fc5604002`; metadata-finalization commit
`96fe5b203e23ed07fd212eb2be56dcc6e5318cc8` is the independently reviewed PR-13R HEAD.
This preserves reviewed PR-13 HEAD `d99c215c5d06153da334de88021393588f177a1e`
as a separate historical fact.

The finalization range `ad5790c26dd26ef374ac96e36eb9283fc5604002..96fe5b203e23ed07fd212eb2be56dcc6e5318cc8`
contains exactly three modified evidence files and no source, test, migration, or architecture file.
