"""Unit tests for BibTeX and RIS parsing (no database, no network)."""

from __future__ import annotations

from researchbase.adapters.reference_files import parse_bibtex, parse_ris

BIB = """
@comment{exported by a reference manager}
@article{sandve2013,
  title = {Ten Simple Rules for {Reproducible} Computational Research},
  author = {Sandve, Geir Kjetil and Nekrutenko, Anton},
  journal = "PLoS Computational Biology",
  year = 2013,
  volume = {9},
  number = {10},
  pages = {e1003285--e1003285},
  doi = {https://doi.org/10.1371/journal.pcbi.1003285}
}
@string{ignored = "x"}
@misc{no-title, note = {nothing useful}}
"""

RIS = """TY  - JOUR
TI  - Nap and memory
AU  - Doe, Jane
AU  - Roe, Richard
PY  - 2021/05/01
JO  - Sleep Journal
VL  - 12
IS  - 3
SP  - 101
EP  - 110
DO  - 10.5555/nap.2021.1
ER  - 

TY  - JOUR
T1  - Second record
ER  -
"""


def test_bibtex_entry_fields_are_normalized():
    (entry,) = parse_bibtex(BIB)
    assert entry["title"] == "Ten Simple Rules for Reproducible Computational Research"
    assert entry["authors"] == ["Geir Kjetil Sandve", "Anton Nekrutenko"]
    assert entry["journal"] == "PLoS Computational Biology"
    assert entry["year"] == "2013"
    assert entry["volume"] == "9"
    assert entry["issue"] == "10"
    assert entry["pages"] == "e1003285--e1003285"
    assert entry["doi"] == "10.1371/journal.pcbi.1003285"


def test_bibtex_skips_comments_strings_and_empty_entries():
    assert [entry["title"] for entry in parse_bibtex(BIB)] == [
        "Ten Simple Rules for Reproducible Computational Research"
    ]


def test_ris_records_are_read_until_end_tag():
    first, second = parse_ris(RIS)
    assert first["title"] == "Nap and memory"
    assert first["authors"] == ["Jane Doe", "Richard Roe"]
    assert first["year"] == "2021"
    assert first["journal"] == "Sleep Journal"
    assert first["volume"] == "12"
    assert first["issue"] == "3"
    assert first["pages"] == "101-110"
    assert first["doi"] == "10.5555/nap.2021.1"
    assert second["title"] == "Second record"
    assert second["doi"] is None


def test_reference_changes_lists_only_differing_fields():
    from researchbase.cli.commands.quick import _reference_changes

    current = {
        "title": "旧标题",
        "authors": [{"name": "甲", "orcid": None}],
        "venue": "期刊",
        "metadata": {"volume": "1", "issue": None, "pages": None},
    }
    reference = {
        "title": "新标题",
        "authors": ["甲"],
        "journal": "期刊",
        "volume": "1",
        "issue": "2",
        "pages": None,
    }
    changes = _reference_changes(current, reference)
    assert changes == {"title": "新标题", "metadata": {"issue": "2"}}


def test_folder_file_matches_by_doi_then_title():
    from researchbase.cli.commands.quick import _match_folder_file

    files = [
        {"file_path": "a.pdf", "title": "Nap and Memory", "doi": "10.1/a"},
        {"file_path": "b.txt", "title": None, "doi": "10.2/B"},
    ]
    by_doi = _match_folder_file({"doi": "10.2/b", "title": "x"}, files)
    assert by_doi is not None and by_doi["file_path"] == "b.txt"
    by_title = _match_folder_file({"doi": None, "title": "nap-and memory!"}, files)
    assert by_title is not None and by_title["file_path"] == "a.pdf"
    assert _match_folder_file({"doi": "10.9/none", "title": "missing"}, files) is None


def test_reference_metadata_has_no_date_from_a_year_only_export():
    from researchbase.cli.commands.quick import _crossref_date, _reference_metadata

    meta = _reference_metadata({"title": "T", "authors": ["甲"], "year": "2021"})
    assert _crossref_date(meta) is None
    assert meta["authors"] == [{"name": "甲", "orcid": None}]


def test_enrich_fills_only_empty_fields():
    from researchbase.cli.commands.quick import _missing_changes

    current = {
        "title": "我的标题",
        "authors": [],
        "venue": "我改过的期刊名",
        "metadata": {"volume": None, "issue": "4", "pages": None},
    }
    reference = {
        "title": "Crossref 标题",
        "authors": ["甲", "乙"],
        "journal": "Crossref 期刊",
        "volume": "9",
        "issue": "1",
        "pages": "1-5",
    }
    changes = _missing_changes(current, reference)
    assert "title" not in changes  # the title is never replaced by enrichment
    assert "venue" not in changes  # an existing value is kept, even if different
    assert changes["authors"] == [{"name": "甲", "orcid": None}, {"name": "乙", "orcid": None}]
    assert changes["metadata"] == {"volume": "9", "pages": "1-5"}
