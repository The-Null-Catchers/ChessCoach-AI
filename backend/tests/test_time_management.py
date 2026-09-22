from app.services.time_management import detect_time_management, parse_simple_time_control


def test_parses_increment_time_control():
    assert parse_simple_time_control("600+5") == (600.0, 5.0)
    assert parse_simple_time_control("180") == (180.0, 0.0)
    assert parse_simple_time_control("40/7200:3600") is None


def test_flags_critical_move_played_too_fast():
    signals = detect_time_management(
        before_clock=180,
        after_clock=179,
        increment=0,
        classification="blunder",
    )
    assert any(item.category == "critical_move_too_fast" for item in signals)


def test_flags_time_trouble_error():
    signals = detect_time_management(
        before_clock=25,
        after_clock=15,
        increment=0,
        classification="mistake",
    )
    assert any(item.category == "time_trouble" for item in signals)
