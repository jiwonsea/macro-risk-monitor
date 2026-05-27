from macro_risk_monitor.engine.units import canonical_unit, convert


def test_percent_to_bps_uses_fred_percent_convention():
    assert convert(0.74, "percent", "bps") == 74


def test_bps_to_percent():
    assert convert(74, "bps", "percent") == 0.74


def test_same_or_unknown_units_are_noop():
    assert convert(4.5, "percent", "percent") == 4.5
    assert convert(4.5, "mystery", "bps") == 4.5


def test_canonical_unit_synonyms():
    assert canonical_unit("%") == "percent"
    assert canonical_unit("bp") == "bps"
