# D01 v0.3 literal byte vectors — PROPOSED

Codec-only synthetic examples, not deployment/installation/binding authority.

| ID | Outcome | Bytes | SHA256 |
| --- | --- | ---: | --- |
| positive-unix-null | ACCEPT_CODEC_ONLY  | 1329 | `1d9ff426679ed07b66352acec2b87539f97f39031806156b0ef7fdba07759701` |
| positive-ipv4 | ACCEPT_CODEC_ONLY  | 1344 | `0e99d845cf7a32d36ba90dc9becf44f0dafd9a76702a9d512310f7cd4f54776f` |
| positive-ipv6 | ACCEPT_CODEC_ONLY  | 1338 | `288c4a6b7605b2d0cfef424a3939b0da54a7101052a443f940a2d4a432505712` |
| positive-acl-empty | ACCEPT_CODEC_ONLY  | 1273 | `0a0ce6f50032acfae767aca287ab230b1fb6986ea9e80c64aeaf219bce14de51` |
| negative-bool-uid | REJECT INTEGER | 1329 | `66c9fc33ce62c45d971a91faa734faea10b96d45a9d869c7a0946435953b0b76` |
| negative-float-uid | REJECT INTEGER | 1331 | `f332b22d10e8c083118416710e0c2ffd740fe980340ffae74057e6b3b03c0366` |
| negative-utc-offset | REJECT UTC | 1334 | `1faebd4395653b58678d5edc0437ea645cf4ef93a9c7ef88959d4f5e1c6d52ca` |
| negative-oid-overflow | REJECT INTEGER | 1334 | `f37440b791be2703e95eea4a38ce5dc8a527b9651588cccd5a9141063ea881a1` |
| negative-role-limit | REJECT ROLE_LIMIT | 9455 | `024ed5689e3c01d57f4f7839d7154fcf1a5fb3f412a681566e9c4358a0cc3119` |
| negative-edge-limit | REJECT EDGE_LIMIT | 11094 | `1b12da3a7b2bd6d03832dbaefa9ee409a5032019dcab6a5e7da7257b3e14ad31` |
| negative-edge-missing-option | REJECT EDGE | 1360 | `b24ccb90598e7294a603d0ea95742e209238e63f5165dae06dabaf3649dfafa3` |
| negative-acl-privilege | REJECT ACL_PRIVILEGE | 1328 | `d244c6e93bedf82dd1ad6984cf52f4613a75dc0baaeba9c887f5b1f3d0985e1d` |
| negative-acl-raw-limit | REJECT ACL_LIMIT | 2130 | `e3ef6e10e5937644cae1650c606538266f7f05417dc75eff4b00a4e32da92f16` |
| negative-config-limit | REJECT ARRAY_LIMIT | 1593 | `0654dc620f702c126421435a389ff2a804625734e15288a5f87025dc41b95604` |
| negative-nfd-text | REJECT NFC | 1330 | `43c94d2a41a8259bad66853601347c4fe0b613ccc11fe7183b0bc7c3eb9cc22e` |
| negative-unix-port-nonnull | REJECT ENDPOINT_NULL | 1329 | `6c2d7231b72a1d553e438ebc40ecdf30d48537c79937ca6f2c46ae541069b98f` |
| negative-ip-noncanonical | REJECT ADDRESS_CANONICAL | 1350 | `a6f292e46deac463cd470df3a3c6593d6e0b39977a0181fa6924e7facf62adb4` |
| negative-ip-remote | REJECT ADDRESS | 1344 | `27cc4411d125b0a6c10f5f37a46c240333ee814beaca192d2fdc57c9fbd1396b` |
| negative-ip-mapped | REJECT ADDRESS | 1351 | `b44baa2d98c0367b2afe1ba0098b54e7c3d32364f3f601264f413abb2838b9b8` |
| negative-missing-position | REJECT RECORD_SHAPE | 1297 | `46650f44b02f6d09843ce077c526585a4f747c5d6a20144d9b72cecadc653f4d` |
| negative-extra-position | REJECT RECORD_SHAPE | 1337 | `6fc73509c802f8017c18d106f7edd48ee6d1b971c4bcb3fd1dd9200d19315b56` |
| negative-wrong-callable | REJECT CALLABLE | 1335 | `e0ea6d5840a005d4d853b6458379b3c43c8a2c06dd817acc31312483ee6ac34a` |
| negative-catalog-extra-field | REJECT CATALOG_SHAPE | 1337 | `445aaaff70044b38f8c7597842376fbf626a99fe2005d29ae461e9eb748f3b89` |
| negative-float4-nan | REJECT FLOAT4_FINITE | 1329 | `610bfab525a4fb7efe3b54067210daa64168ea3eb4d1c002ddf96e28d9b4203c` |
| negative-acl-null-empty-confusion | REJECT ACL_NULL | 1327 | `a063e96a5544c3123f8357f844be7c9f2a4d88b5b9399d13ae97d7874b6d1248` |
| negative-unsafe-path | REJECT PATH | 1332 | `534dbce7f8e5f660f3264cac2a03f6fb81638c299c32c668c56c8710bca69aec` |
| negative-oversized-body | REJECT TEXT_LIMIT | 9510 | `3b5fc2f4e1c8e49c87dfab1a0dceb4be0391019a624b8ff3b6367eefe47ec32f` |
| negative-set-owner-reachable | REJECT OWNER_REACHABLE | 1365 | `8cbf1838f6323088214c3082e63053d2d6bc4d899527d3c8f0e5bfaab2df74ba` |
| negative-inherit-owner-reachable | REJECT OWNER_REACHABLE | 1365 | `e6d7f4e1af73f921c96371d210a97beb50de14f2012a167956003964932c1ec1` |
| positive-restricted-membership | ACCEPT_CODEC_ONLY  | 1437 | `ea26059f1215305e234b39871a209c2910010dcdbbb7de4023a06219f9cf1167` |
| negative-expected-membership-inherit | REJECT APPROVED_BINDING_MISMATCH | 1436 | `d1e87b0d8dac6892c465dd42e8bfe059f3d942927fd5016468c6b3c6cc02870a` |
| negative-expected-membership-set | REJECT APPROVED_BINDING_MISMATCH | 1436 | `ba5413d2866714cab4a8d7a16b506fcef8a5873e29dc9f4104ee87fbe5aeadaf` |
| negative-transitive-owner | REJECT OWNER_REACHABLE | 1474 | `bc6552ac283bbcdae3ecd16638963805dfe9982c2e0a42bd1f56f871d062e235` |
| negative-expiry-equality | REJECT EXPIRED | 1329 | `1d9ff426679ed07b66352acec2b87539f97f39031806156b0ef7fdba07759701` |
| negative-extra-whitespace | REJECT NONCANONICAL_BYTES | 1330 | `60e48e105f99f9c0d59af2e1e897fd139b6022123b77b75531d2d009e020eae4` |
| negative-unicode-escape-alias | REJECT NONCANONICAL_BYTES | 1333 | `b48d604a8bcdaef41186207795023c07cae7b21be302d6ed2c890efb9b1abcfd` |
| negative-trailing-data | REJECT JSON | 1331 | `53c5e538fcd610dabcc44cc09354103775bf818a1137a6174a1e3a6324e68fa2` |
| negative-bom | REJECT DOMAIN | 1332 | `e3c4c1f4c7bd65bb2370c61cb2c989b83d9cad598fd6b3e70c38d46c7ca5ba4f` |
| negative-invalid-utf8 | REJECT JSON | 35 | `c3cf603ce26812b934d1be37ea1ac13e2f53c5a85d0d2dcd023b294942f4c124` |
| negative-record-limit | REJECT RECORD_LIMIT | 65569 | `1b3b04bb1bbb529e65a52c3a4e56cba08f67a2e52389a3336499dfe271b462e2` |
| negative-expected-acl-null | REJECT APPROVED_BINDING_MISMATCH | 1273 | `0a0ce6f50032acfae767aca287ab230b1fb6986ea9e80c64aeaf219bce14de51` |
| negative-expected-role-option | REJECT APPROVED_BINDING_MISMATCH | 1330 | `2e7f440d3babb75e2eb9a02154f1ca6b0d8ca7663961abdf6a3ce1e63965e6e4` |
| negative-control-host-DEL | REJECT TEXT | 1321 | `26b7ac785a6aeb2b23f27abd7e8fb4301f9623ba3653e7377153ed72e95c7beb` |
| negative-control-path-DEL | REJECT TEXT | 1330 | `1e6e8b44384c60e3baa39e8481444def7554bca5ba7637ccafaf728f46898523` |
| negative-control-body-DEL | REJECT TEXT | 1329 | `315d9190ce8935cf46c37fb12261049c152b096eb4e4e79700fd81d4cdef083e` |
| negative-control-host-C1 | REJECT TEXT | 1322 | `e0b1f453206cf15fc5fb7a374764ab70e4eb5cd430ab1e36e6d659f726b31900` |
| negative-control-path-C1 | REJECT TEXT | 1331 | `64019f841fda0557210a4b75c39efb230cc798d95a18f3b49ff2636329d46607` |
| negative-control-body-C1 | REJECT TEXT | 1330 | `d214d483bbdbfb31a2281ff0dfee75d9c7c9ecebf5ac8996fe9185d4bbc7c46a` |
| negative-depth15000-array | REJECT JSON_DEPTH | 30033 | `3f8fe7ecda17d24483e46073dcfc54e521d2941251c060ba78211b0802ecee74` |
| negative-depth9-object | REJECT JSON_DEPTH | 87 | `bc7bccd01021d845038a428ed4f344cfd1cd574fbb300c5efa9d44715897e6ea` |
| negative-depth9-array | REJECT JSON_DEPTH | 51 | `ac63557304af50a56fe3ca31dc0964a31e9337bbeb0382f25e4bc90aad156828` |
| negative-depth8-wrong-record | REJECT RECORD_SHAPE | 49 | `03539fe28c270a9037b764b77233a2905acc047c4cfaaeac60e370aaec44219d` |
| negative-integer5000-digits | REJECT JSON_INTEGER_LIMIT | 5034 | `64f369b346711df48dd85a4dbf2b18f373ff913ed0b07b0e9ff4aa7be7f7b5fe` |
| positive-quoted-brackets-escapes | ACCEPT_CODEC_ONLY  | 1360 | `43edd6f2a772b49eb72203aca70f3f6a27e801f1f9e05c6b15b1169e4e7af3fa` |
| positive-body-HT-LF-CR | ACCEPT_CODEC_ONLY  | 1355 | `917f9b8c7566ce2439a2b1cacddf3e0005b6f1e62925a4c8ff7929bf61f0b254` |
