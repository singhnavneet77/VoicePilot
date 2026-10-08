from engine.experiment import assign_variant


def test_assignment_is_sticky():
    first = assign_variant("lead-123", "exp-1", 0.10)
    second = assign_variant("lead-123", "exp-1", 0.10)
    assert first == second


def test_assignment_changes_with_experiment():
    a = assign_variant("lead-123", "exp-1", 0.50)
    b = assign_variant("lead-123", "exp-2", 0.50)
    # Different experiment IDs are allowed to assign differently.
    assert a in {"A", "B"}
    assert b in {"A", "B"}


def test_split_bounds():
    try:
        assign_variant("lead", "exp", 0)
        assert False
    except ValueError:
        pass
