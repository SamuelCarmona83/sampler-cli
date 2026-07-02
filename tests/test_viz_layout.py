from sampler.viz.layout_algo import (
    ease_out_cubic,
    expand_from_center,
    fruchterman_reingold,
    radial_layout,
)


def test_fruchterman_reingold_square_bounds() -> None:
    nodes = [1, 2, 3, 4]
    edges = [(1, 2), (2, 3), (3, 4)]
    pos = fruchterman_reingold(nodes, edges, iterations=10, seed=1)
    assert set(pos.keys()) == set(nodes)
    for x, y in pos.values():
        assert 12 <= x <= 88
        assert 12 <= y <= 88


def test_expand_from_center_starts_at_middle() -> None:
    targets = {1: (80.0, 80.0), 2: (20.0, 20.0)}
    at_zero = expand_from_center(targets, 0.0)
    assert at_zero[1] == (50.0, 50.0)
    assert at_zero[2] == (50.0, 50.0)


def test_expand_from_center_reaches_targets() -> None:
    targets = {1: (80.0, 80.0)}
    at_one = expand_from_center(targets, 1.0)
    assert at_one[1][0] == 80.0
    assert at_one[1][1] == 80.0


def test_radial_layout_spreads_nodes() -> None:
    pos = radial_layout([1, 2, 3, 4])
    xs = {p[0] for p in pos.values()}
    assert len(xs) > 2


def test_ease_out_cubic_endpoints() -> None:
    assert ease_out_cubic(0.0) == 0.0
    assert ease_out_cubic(1.0) == 1.0