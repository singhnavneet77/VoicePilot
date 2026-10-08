from engine.stats import compare_binary_rates, decide


def test_clear_win():
    d = decide(800, 10000, 1100, 10000, alpha=0.01, min_per_arm=1000)
    assert d.status == "WIN"
    assert d.lift > 0


def test_clear_stop():
    d = decide(1000, 10000, 500, 10000, alpha=0.01, min_per_arm=1000)
    assert d.status == "STOP"
    assert d.lift < 0


def test_inconclusive_small_sample():
    d = decide(10, 100, 12, 100, alpha=0.01, min_per_arm=1000)
    assert d.status == "INCONCLUSIVE"


def test_rate_comparison():
    p, diff, lo, hi = compare_binary_rates(100, 1000, 120, 1000)
    assert 0 <= p <= 1
    assert diff == 0.02
    assert lo < diff < hi
