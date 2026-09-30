from perfume_journal.models import PerfumeCreate


def test_canonicalizes_known_abbreviation() -> None:
    perf1 = PerfumeCreate(brand="Creed", name="Aventus", concentration="edp")
    perf2 = PerfumeCreate(brand="Creed", name="Aventus", concentration="eDt")
    perf3 = PerfumeCreate(
        brand="Creed", name="Aventus", concentration="Extrait de Parfum"
    )
    perf4 = PerfumeCreate(
        brand="Creed",
        name="Aventus",
    )

    assert perf1.concentration == "EDP"
    assert perf2.concentration == "EDT"
    assert perf3.concentration == "Extrait de Parfum"
    assert perf4.concentration is None
    assert perf1.brand == "Creed"
    assert perf1.name == "Aventus"
