# Phase 1 accepted commit inventory

Canonical accepted state: `5fe5dd90310d68d6df1683307f0d24dd2233c3dd`. All SHA values below were resolved from Git; every implementation, evidence and endpoint SHA passed `git merge-base --is-ancestor <sha> 5fe5dd90310d68d6df1683307f0d24dd2233c3dd`.

Acceptance authority: the supplied final independent review (ACCEPT WITH P3), corroborated by tracked PR-17R exit/finding records. This inventory does not re-approve intermediate snapshots. Original PR rows describe retained work, accepted cumulatively after the remediation rows. Historical FAIL/BLOCKED states remain history and are not alternative baseline targets.

Method: use chronological phase endpoints from Git subjects plus each evidence directory; resolve the last commit touching src/tests/migrations/pyproject.toml/uv.lock at that endpoint for the implementation/test head, and the last commit touching that phase evidence directory for its evidence head. A mixed commit is allowed; evidence head can precede a later test-only correction. The machine-readable companion preserves per-period commits and the fingerprint as it existed at that endpoint, avoiding later overwritten subject metadata.

| PR / accepted closure | Implementation/test HEAD | Evidence HEAD | Final disposition | Ancestor of accepted HEAD |
|---|---|---|---|---|
| PR-00 | `565fbc95db53b1c7534bacb41870e941c5d10101` | `ce4fe585388da7026523473ae01834022277eadc` | Accepted in final cumulative state | YES / YES |
| PR-01 | `a517b3174f14ac2f1fb9dd3ead1852404585aa75` | `647facf1fc4e6973f131a3e3ff64b49c3f81e349` | Retained; acceptance completed by remediation | YES / YES |
| PR-01R | `c3e7497046b5c0213f18c619e7e587a0f18165e6` | `99e088812e8ce86ddaceec7f731bc9ae913c33e0` | Accepted in final cumulative state | YES / YES |
| PR-02 | `dd69bbff27971b9ce4065d06a321f3c278e728a1` | `57a8d156fb8cd3a15de16b48b211ef433437fdf9` | Retained; acceptance completed by remediation | YES / YES |
| PR-02R | `1fbb4634066cbcd49454590609486dfcebeca30f` | `99e402cc01bb189925bcfae0db6ba0016b4ccde9` | Accepted in final cumulative state | YES / YES |
| PR-03 | `9929df67f7b8c296c25ff680faec257048b5a050` | `4ab6af705aab50af0a13d9289543eb9a21ea2053` | Retained; acceptance completed by remediation | YES / YES |
| PR-03R | `49fcf2feca35ea8c07832f7eaeed856b141004ed` | `4dfffd882dd103f292474af2431d9ec42ff82618` | Accepted in final cumulative state | YES / YES |
| PR-04 | `4c738660f7f46995ef32c413715ecce73a1028da` | `059641c8445749ebdac11786be40185ba8644004` | Retained; acceptance completed by remediation | YES / YES |
| PR-04R (+ R2) | `8dd77d39c0962439003667083120fa7a81395020` | `eda94d650a66bc693a21a2948200aae60ee357d7` | Accepted in final cumulative state | YES / YES |
| PR-05 | `f11f3eec619daaff0761bd1911e3f29aab838330` | `1ab60334f261b0e11f98e76d8416bc7ef5afa7d6` | Retained; acceptance completed by remediation | YES / YES |
| PR-05R (+ R2/R3) | `0269e69b59a1153ccf4f7dbb9acdb6b4c135061b` | `f9affdcda22e207e2249dcd2180ba4463a8d4e13` | Accepted in final cumulative state | YES / YES |
| PR-06 | `a5c53e2c7e11a79b8e6cd38f0b301d2271ce3764` | `c92f11993c675764f0f93fe30017ad312e535cb0` | Retained; acceptance completed by remediation | YES / YES |
| PR-06R | `f2edf4766838c3678b58536f5ee60306664d8894` | `0514df0d5c8bc38b3cda86d0afe29ffd50758df2` | Accepted in final cumulative state | YES / YES |
| PR-07 (+ R/R2) | `b7e7a537c17bd7e35cc19bb52da618054b19da0f` | `f965abb3f2223d84690b597541d6bba316365423` | Accepted in final cumulative state | YES / YES |
| PR-08 | `9a7ff99292bd7b1fef3d819ced8d5ea098069040` | `275de4151f2843e096b8cf036d5451fe0a4b23e8` | Accepted in final cumulative state | YES / YES |
| PR-09 (+ R..R6) | `8a57413145d27864d41ffb3c8596a205a7cb4fb8` | `fe8027dfef4f585566a60f467f66fdd8116e0964` | Accepted in final cumulative state | YES / YES |
| PR-10 (+ R/R2) | `9c5a87a4567f4fb1c09b4dcd1d3c337f3d827e7d` | `934e8690fc3f8459b1632e896f5c3be01abf8c1f` | Accepted in final cumulative state | YES / YES |
| PR-11 (+ R..R7) | `813aaebd8749e6ca1553802f0930dca04a0f21d0` | `18fb4138e7ccb57809ea54b916f52d8b801b8bec` | Accepted in final cumulative state | YES / YES |
| PR-12 (+ R..R3) | `e95fee5e59c97d78cf4ebe6c86f195c86b3ab759` | `5b4d7e1ffa3509adbb2f324d2fb82df9883780cb` | Accepted in final cumulative state | YES / YES |
| PR-13 (+ R..R3) | `2f6f3b7f1f49eece5231af1aab4ef6e81527e0c3` | `e57cc7f47250a2c5156387cc1e04bb7888537e6c` | Accepted in final cumulative state | YES / YES |
| PR-14 (+ corrections through R7) | `701df464c55d8993c7b14690bcea75594d553553` | `ce94d738129fee584744c1a7e1eef8fd334ea225` | Accepted in final cumulative state | YES / YES |
| PR-15 (+ R) | `f05f33e6e16f6d7159fc0b3a93e5440f227d860a` | `912f564ff3f8a5e9d4be562f2ed5734eaeaed8f1` | Accepted in final cumulative state | YES / YES |
| PR-16 | `fac20936a462167eb652dee07ad8a5c0a3612b27` | `390cbda614215c439766ce805947d339772dc55a` | Retained; acceptance completed by remediation | YES / YES |
| PR-16R | `fac20936a462167eb652dee07ad8a5c0a3612b27` | `0eed8d85f4009a4f5265a697476423b7cdaf8ea4` | Accepted in final cumulative state | YES / YES |
| PR-17 | `745de1b0cb90e6f590fc28f2da1e0317809e3e5a` | `03ccba54b8c983815f74d08a2390e0dfa45f8551` | Retained; acceptance completed by remediation | YES / YES |
| PR-17R | `2d8e2abe31d0410717412c182d3cf7bd0811cced` | `5fe5dd90310d68d6df1683307f0d24dd2233c3dd` | FINAL ACCEPT WITH P3; gates PASS | YES / YES |

## Detailed historical lineage (not independent accepted baseline targets)

| Period | Historical endpoint | Implementation/test head | Evidence head / kind | Source at endpoint |
|---|---|---|---|---|
| PR-00 | `ce4fe585388da7026523473ae01834022277eadc` | `565fbc95db53b1c7534bacb41870e941c5d10101` | `ce4fe585388da7026523473ae01834022277eadc` (evidence-only) | `artifacts/pr_evidence/PR-00/harness_fingerprint.json` |
| PR-01 | `647facf1fc4e6973f131a3e3ff64b49c3f81e349` | `a517b3174f14ac2f1fb9dd3ead1852404585aa75` | `647facf1fc4e6973f131a3e3ff64b49c3f81e349` (evidence-only) | `artifacts/pr_evidence/PR-01/harness_fingerprint.json` |
| PR-01R | `99e088812e8ce86ddaceec7f731bc9ae913c33e0` | `c3e7497046b5c0213f18c619e7e587a0f18165e6` | `99e088812e8ce86ddaceec7f731bc9ae913c33e0` (evidence-only) | `artifacts/pr_evidence/PR-01R/harness_fingerprint.json` |
| PR-02 | `57a8d156fb8cd3a15de16b48b211ef433437fdf9` | `dd69bbff27971b9ce4065d06a321f3c278e728a1` | `57a8d156fb8cd3a15de16b48b211ef433437fdf9` (evidence-only) | `artifacts/pr_evidence/PR-02/harness_fingerprint.json` |
| PR-02R | `99e402cc01bb189925bcfae0db6ba0016b4ccde9` | `1fbb4634066cbcd49454590609486dfcebeca30f` | `99e402cc01bb189925bcfae0db6ba0016b4ccde9` (evidence-only) | `artifacts/pr_evidence/PR-02R/harness_fingerprint.json` |
| PR-03 | `4ab6af705aab50af0a13d9289543eb9a21ea2053` | `9929df67f7b8c296c25ff680faec257048b5a050` | `4ab6af705aab50af0a13d9289543eb9a21ea2053` (evidence-only) | `artifacts/pr_evidence/PR-03/harness_fingerprint.json` |
| PR-03R | `4dfffd882dd103f292474af2431d9ec42ff82618` | `49fcf2feca35ea8c07832f7eaeed856b141004ed` | `4dfffd882dd103f292474af2431d9ec42ff82618` (evidence-only) | `artifacts/pr_evidence/PR-03R/harness_fingerprint.json` |
| PR-04 | `059641c8445749ebdac11786be40185ba8644004` | `4c738660f7f46995ef32c413715ecce73a1028da` | `059641c8445749ebdac11786be40185ba8644004` (evidence-only) | `artifacts/pr_evidence/PR-04/harness_fingerprint.json` |
| PR-04R | `0573fa5ee0886e1a2bdaa1026ccfb548b3523980` | `c6be24bc27e32d0e16452e7a79195e3b09609d5a` | `0573fa5ee0886e1a2bdaa1026ccfb548b3523980` (evidence-only) | `artifacts/pr_evidence/PR-04R/harness_fingerprint.json` |
| PR-04R2 | `eda94d650a66bc693a21a2948200aae60ee357d7` | `8dd77d39c0962439003667083120fa7a81395020` | `eda94d650a66bc693a21a2948200aae60ee357d7` (evidence-only) | `artifacts/pr_evidence/PR-04R2/harness_fingerprint.json` |
| PR-05 | `1ab60334f261b0e11f98e76d8416bc7ef5afa7d6` | `f11f3eec619daaff0761bd1911e3f29aab838330` | `1ab60334f261b0e11f98e76d8416bc7ef5afa7d6` (evidence-only) | `artifacts/pr_evidence/PR-05/harness_fingerprint.json` |
| PR-05R | `5ca4dd8c9e083b5370014d86789e82c6e9c5b8ac` | `da7a81f1c9dd0da8d0dab619eac6e80c54aa1444` | `5ca4dd8c9e083b5370014d86789e82c6e9c5b8ac` (evidence-only) | `artifacts/pr_evidence/PR-05R/harness_fingerprint.json` |
| PR-05R2 | `66c4f3d4a4e11a349f2b99aca21cb27c16f82494` | `20e3b0fe18e1759e1615ada0047b683cc49b3132` | `66c4f3d4a4e11a349f2b99aca21cb27c16f82494` (evidence-only) | `artifacts/pr_evidence/PR-05R2/harness_fingerprint.json` |
| PR-05R3 | `403a26ca3ca24f837c736d69ef1eac6002fda075` | `0269e69b59a1153ccf4f7dbb9acdb6b4c135061b` | `f9affdcda22e207e2249dcd2180ba4463a8d4e13` (evidence-only) | `artifacts/pr_evidence/PR-05R3/harness_fingerprint.json` |
| PR-06 | `c92f11993c675764f0f93fe30017ad312e535cb0` | `a5c53e2c7e11a79b8e6cd38f0b301d2271ce3764` | `c92f11993c675764f0f93fe30017ad312e535cb0` (evidence-only) | `artifacts/pr_evidence/PR-06/harness_fingerprint.json` |
| PR-06R | `f2edf4766838c3678b58536f5ee60306664d8894` | `f2edf4766838c3678b58536f5ee60306664d8894` | `0514df0d5c8bc38b3cda86d0afe29ffd50758df2` (mixed implementation/test + evidence) | `artifacts/pr_evidence/PR-06R/harness_fingerprint.json` |
| PR-07 | `52a962ab751119c906ba77e87108273574d334b6` | `4e2327b1cd292a887175f78a2f4b713b05e5511d` | `52a962ab751119c906ba77e87108273574d334b6` (evidence-only) | `artifacts/pr_evidence/PR-07/harness_fingerprint.json` |
| PR-07R | `82196727b0357797442454b94505af0615b60269` | `fe888f334fe6e80a74a17c06d22e18e03f6f68d5` | `82196727b0357797442454b94505af0615b60269` (evidence-only) | `artifacts/pr_evidence/PR-07R/harness_fingerprint.json` |
| PR-07R2 | `f965abb3f2223d84690b597541d6bba316365423` | `b7e7a537c17bd7e35cc19bb52da618054b19da0f` | `f965abb3f2223d84690b597541d6bba316365423` (evidence-only) | `artifacts/pr_evidence/PR-07R2/harness_fingerprint.json` |
| PR-08 | `275de4151f2843e096b8cf036d5451fe0a4b23e8` | `9a7ff99292bd7b1fef3d819ced8d5ea098069040` | `275de4151f2843e096b8cf036d5451fe0a4b23e8` (evidence-only) | `artifacts/pr_evidence/PR-08/harness_fingerprint.json` |
| PR-09 | `8e67b4890a55740f73728ab40f08e8543f177dba` | `17a5f66b10e9ca2eef7bcf1bfa1f9831584d2149` | `8e67b4890a55740f73728ab40f08e8543f177dba` (evidence-only) | `artifacts/pr_evidence/PR-09/harness_fingerprint.json` |
| PR-09R | `9a35f9f460dd20e1b4660d3b8103f1531b489398` | `e879ad852ad81737a3b440729d285f506eaff41b` | `9a35f9f460dd20e1b4660d3b8103f1531b489398` (evidence-only) | `artifacts/pr_evidence/PR-09R/harness_fingerprint.json` |
| PR-09R2 | `9c473814877c10c440c2ca11f194dbfb58cd2403` | `89c033096eb8295e4e46dbe3bdbea003b86498a9` | `9c473814877c10c440c2ca11f194dbfb58cd2403` (evidence-only) | `artifacts/pr_evidence/PR-09R2/harness_fingerprint.json` |
| PR-09R3 | `0feba305ce8d798e1257b93c7695a768ded72899` | `197bd2da996c55c09b2cad0ff66ebe97dd632623` | `0feba305ce8d798e1257b93c7695a768ded72899` (evidence-only) | `artifacts/pr_evidence/PR-09R3/harness_fingerprint.json` |
| PR-09R4 | `602f22478c6919f2611ff436b4199a81fa6b8297` | `8a57413145d27864d41ffb3c8596a205a7cb4fb8` | `602f22478c6919f2611ff436b4199a81fa6b8297` (evidence-only) | `artifacts/pr_evidence/PR-09R4/harness_fingerprint.json` |
| PR-09R5 | `ecb9adaf6aebef73fb45d344197ea9e18ad37d9c` | `8a57413145d27864d41ffb3c8596a205a7cb4fb8` | `ecb9adaf6aebef73fb45d344197ea9e18ad37d9c` (evidence-only) | `artifacts/pr_evidence/PR-09R5/harness_fingerprint.json` |
| PR-09R6 | `fe8027dfef4f585566a60f467f66fdd8116e0964` | `8a57413145d27864d41ffb3c8596a205a7cb4fb8` | `fe8027dfef4f585566a60f467f66fdd8116e0964` (evidence-only) | `artifacts/pr_evidence/PR-09R6/harness_fingerprint.json` |
| PR-10 | `41a886344f277e84c7d63891c5b4351262329e30` | `0661a584aff47537c24e537edcef7946f8f0129b` | `41a886344f277e84c7d63891c5b4351262329e30` (evidence-only) | `artifacts/pr_evidence/PR-10/harness_fingerprint.json` |
| PR-10R | `bffb95c3dc239219ec4c288eaa3c9991f7733f6c` | `9c5a87a4567f4fb1c09b4dcd1d3c337f3d827e7d` | `bffb95c3dc239219ec4c288eaa3c9991f7733f6c` (evidence-only) | `artifacts/pr_evidence/PR-10R/harness_fingerprint.json` |
| PR-10R2 | `934e8690fc3f8459b1632e896f5c3be01abf8c1f` | `9c5a87a4567f4fb1c09b4dcd1d3c337f3d827e7d` | `934e8690fc3f8459b1632e896f5c3be01abf8c1f` (evidence-only) | `artifacts/pr_evidence/PR-10R2/harness_fingerprint.json` |
| PR-11 | `9592b66dc3372fae18fdd66555203f0788e407e2` | `5093639b7ebdfa205c0304aa9914603fb6f13d11` | `9592b66dc3372fae18fdd66555203f0788e407e2` (evidence-only) | `artifacts/pr_evidence/PR-11/harness_fingerprint.json` |
| PR-11R | `6675a7444cdb897d1bf810a55b32b6d88015ea15` | `4aa969e7781dd6fd36e7d98999153098af264095` | `6675a7444cdb897d1bf810a55b32b6d88015ea15` (evidence-only) | `artifacts/pr_evidence/PR-11R/harness_fingerprint.json` |
| PR-11R2 | `e62d19f97c965003492648df84a220a25b3ebffa` | `2304c081f668a01a7663624a271728431a9ba745` | `e62d19f97c965003492648df84a220a25b3ebffa` (evidence-only) | `artifacts/pr_evidence/PR-11R2/harness_fingerprint.json` |
| PR-11R3 | `716e316d57d4dc40b4c13586f3dfafebdc17caba` | `813aaebd8749e6ca1553802f0930dca04a0f21d0` | `716e316d57d4dc40b4c13586f3dfafebdc17caba` (evidence-only) | `artifacts/pr_evidence/PR-11R3/harness_fingerprint.json` |
| PR-11R4 | `5f3626d97ba129ab8487d5ce134fa87bba3312bb` | `813aaebd8749e6ca1553802f0930dca04a0f21d0` | `5f3626d97ba129ab8487d5ce134fa87bba3312bb` (evidence-only) | `artifacts/pr_evidence/PR-11R4/harness_fingerprint.json` |
| PR-11R5 | `10a4e761eecda6e2a2b44b06d60400b43265e458` | `813aaebd8749e6ca1553802f0930dca04a0f21d0` | `10a4e761eecda6e2a2b44b06d60400b43265e458` (evidence-only) | `artifacts/pr_evidence/PR-11R5/harness_fingerprint.json` |
| PR-11R6 | `adc78c84516c5779b46db103d35221afc810add3` | `813aaebd8749e6ca1553802f0930dca04a0f21d0` | `adc78c84516c5779b46db103d35221afc810add3` (evidence-only) | `artifacts/pr_evidence/PR-11R6/harness_fingerprint.json` |
| PR-11R7 | `18fb4138e7ccb57809ea54b916f52d8b801b8bec` | `813aaebd8749e6ca1553802f0930dca04a0f21d0` | `18fb4138e7ccb57809ea54b916f52d8b801b8bec` (evidence-only) | `artifacts/pr_evidence/PR-11R7/harness_fingerprint.json` |
| PR-12 | `9244ac1ca920c2a7d8777e7f1fbbdcab0fda27e2` | `019148ed853c480f056975c2fa156a35abeea735` | `9244ac1ca920c2a7d8777e7f1fbbdcab0fda27e2` (evidence-only) | `artifacts/pr_evidence/PR-12/harness_fingerprint.json` |
| PR-12R | `3564361bb3b80a9302b48ed61b1b0b1fa773de26` | `054fb27f7007abf38a42b8dc674996e86b8038eb` | `3564361bb3b80a9302b48ed61b1b0b1fa773de26` (evidence-only) | `artifacts/pr_evidence/PR-12R/harness_fingerprint.json` |
| PR-12R2 | `b973356f494bb75a2f324be8455a9f54934e9f5d` | `e95fee5e59c97d78cf4ebe6c86f195c86b3ab759` | `b973356f494bb75a2f324be8455a9f54934e9f5d` (evidence-only) | `artifacts/pr_evidence/PR-12R2/harness_fingerprint.json` |
| PR-12R3 | `5b4d7e1ffa3509adbb2f324d2fb82df9883780cb` | `e95fee5e59c97d78cf4ebe6c86f195c86b3ab759` | `5b4d7e1ffa3509adbb2f324d2fb82df9883780cb` (evidence-only) | `artifacts/pr_evidence/PR-12R3/harness_fingerprint.json` |
| PR-13 | `d99c215c5d06153da334de88021393588f177a1e` | `92302831438bec7db163e5ec4de8e6f63dc97d6b` | `d99c215c5d06153da334de88021393588f177a1e` (evidence-only) | `artifacts/pr_evidence/PR-13/harness_fingerprint.json` |
| PR-13R | `96fe5b203e23ed07fd212eb2be56dcc6e5318cc8` | `b6afdb78a08ae29070291d73959098a9f11087a9` | `96fe5b203e23ed07fd212eb2be56dcc6e5318cc8` (evidence-only) | `artifacts/pr_evidence/PR-13R/harness_fingerprint.json` |
| PR-13R2 | `19429024924469cf37b7e3ac31de53e72130c632` | `1c8479aa8f36b3820796c42152b1b5ebeb6e3162` | `19429024924469cf37b7e3ac31de53e72130c632` (evidence-only) | `artifacts/pr_evidence/PR-13R2/harness_fingerprint.json` |
| PR-13R3 | `e57cc7f47250a2c5156387cc1e04bb7888537e6c` | `2f6f3b7f1f49eece5231af1aab4ef6e81527e0c3` | `e57cc7f47250a2c5156387cc1e04bb7888537e6c` (evidence-only) | `artifacts/pr_evidence/PR-13R3/harness_fingerprint.json` |
| PR-14 | `16695506f285fe015eb15948bb5b07f95f5944aa` | `701df464c55d8993c7b14690bcea75594d553553` | `16695506f285fe015eb15948bb5b07f95f5944aa` (evidence-only) | `artifacts/pr_evidence/PR-14/harness_fingerprint.json` |
| PR-14R2 | `3a9cb09ca0c7a84a43c6c12e752c5e41892c3449` | `701df464c55d8993c7b14690bcea75594d553553` | `3a9cb09ca0c7a84a43c6c12e752c5e41892c3449` (evidence-only) | `artifacts/pr_evidence/PR-14R2/harness_fingerprint.json` |
| PR-14R3 | `c4b324ab5d29a71fce999c2a801e62c8a124a77d` | `701df464c55d8993c7b14690bcea75594d553553` | `c4b324ab5d29a71fce999c2a801e62c8a124a77d` (evidence-only) | `artifacts/pr_evidence/PR-14R3/harness_fingerprint.json` |
| PR-14R4 | `724c67d4411fac7904470301cef80af18f1507a0` | `701df464c55d8993c7b14690bcea75594d553553` | `724c67d4411fac7904470301cef80af18f1507a0` (evidence-only) | `artifacts/pr_evidence/PR-14R4/harness_fingerprint.json` |
| PR-14R5 | `b1a1f16e9972618b8115488baceb293279f901f7` | `701df464c55d8993c7b14690bcea75594d553553` | `b1a1f16e9972618b8115488baceb293279f901f7` (evidence-only) | `artifacts/pr_evidence/PR-14R5/harness_fingerprint.json` |
| PR-14R7 | `ce94d738129fee584744c1a7e1eef8fd334ea225` | `701df464c55d8993c7b14690bcea75594d553553` | `ce94d738129fee584744c1a7e1eef8fd334ea225` (evidence-only) | `artifacts/pr_evidence/PR-14R7/harness_fingerprint.json` |
| PR-15 | `71ee20e65f45dc5e2fd413371d23836fc10fd6a7` | `71ee20e65f45dc5e2fd413371d23836fc10fd6a7` | `1afe9845fb04cbbb243b290aecea84e6b74f1b0c` (mixed implementation/test + evidence) | `artifacts/pr_evidence/PR-15/harness_fingerprint.json` |
| PR-15R | `912f564ff3f8a5e9d4be562f2ed5734eaeaed8f1` | `f05f33e6e16f6d7159fc0b3a93e5440f227d860a` | `912f564ff3f8a5e9d4be562f2ed5734eaeaed8f1` (evidence-only) | `artifacts/pr_evidence/PR-15R/harness_fingerprint.json` |
| PR-16 | `390cbda614215c439766ce805947d339772dc55a` | `fac20936a462167eb652dee07ad8a5c0a3612b27` | `390cbda614215c439766ce805947d339772dc55a` (evidence-only) | `artifacts/pr_evidence/PR-16/harness_fingerprint.json` |
| PR-16R | `0eed8d85f4009a4f5265a697476423b7cdaf8ea4` | `fac20936a462167eb652dee07ad8a5c0a3612b27` | `0eed8d85f4009a4f5265a697476423b7cdaf8ea4` (evidence-only) | `artifacts/pr_evidence/PR-16R/harness_fingerprint.json` |
| PR-17 | `03ccba54b8c983815f74d08a2390e0dfa45f8551` | `745de1b0cb90e6f590fc28f2da1e0317809e3e5a` | `03ccba54b8c983815f74d08a2390e0dfa45f8551` (evidence-only) | `artifacts/pr_evidence/PR-17/harness_fingerprint.json` |
| PR-17R | `5fe5dd90310d68d6df1683307f0d24dd2233c3dd` | `2d8e2abe31d0410717412c182d3cf7bd0811cced` | `5fe5dd90310d68d6df1683307f0d24dd2233c3dd` (evidence-only) | `artifacts/pr_evidence/PR-17R/harness_fingerprint.json` |

All 58 period endpoints form one ancestor chain. The full commit subjects, endpoint fingerprints and exact refs are in [raw/commit_inventory.json](raw/commit_inventory.json). Earlier remediation/evidence snapshots are superseded as final-state candidates, without removing their ancestor commits.

## Excluded branch and metadata reconciliation

- `pr16-history-backup` ends at `e601aa42532700194f54e578e829e44bbf434101`. Its only three non-ancestor commits are patch-equivalent to accepted history: `c9574d68bad0a896dc9ae0ed757e50c9aff0b0ca` → `abf91e949c33682589f0f1e82fcaf9b092efa981`; `3659ba35303930e35c225632a4d383b0d3dfa257` → `fac20936a462167eb652dee07ad8a5c0a3612b27`; `e601aa42532700194f54e578e829e44bbf434101` → `e9f070013afefe7af00dd69506d4d9c71d93ea73`.
- Both corresponding endpoint trees are `992b11553cff9dbb6c0a08bc0b64631f54472a45`; the complete tree diff is empty. Therefore this is an old duplicate history branch, not missing accepted functionality. Do not merge it.
- `master` and `codex/pr-01r-remediation` are ancestors of the accepted HEAD. The integration branch is `codex/pr-02`, despite its historical name. No remote is configured; the audit covers every locally available ref and tracked repository evidence.
- PR-14 original fingerprint still says BLOCKED: it is historical, superseded by PR-14R7 reconciliation. PR-14R is represented by the PR-14 implementation/evidence range. PR-14R6 produced no commit or evidence package, explicitly documented in `artifacts/pr_evidence/PR-14R7/reviewed_subject_reconciliation.md`; no SHA is invented.
- PR-15 initial fingerprint points at its parent subject and lives in a mixed feature/evidence commit. Git identifies the actual implementation and final accepted PR-15R subject (`f05f33e…`) and evidence (`912f564…`); the stale original fingerprint is not promoted to final authority.
- PR-17 historical evidence was updated by PR-17R. Historical PR-17 endpoint `03ccba5…` and its subject `745de1b…` are resolved at that historical endpoint; current PR-17/PR-17R fingerprints correctly refer to the final remediation subject `2d8e2ab…`.
- Pre-existing untracked execution packs, plans, `.DS_Store` files and `artifacts/pr-12R/` are not part of the accepted Git tree. They are preserved and excluded from this consolidation commit (see raw/starting_status.txt).
- No missing accepted commit, independent experimental/debug branch, PR-18 implementation or Phase 2 implementation was found in available refs. No merge, reset, rebase, rewrite, deletion of evidence history or push is performed.
