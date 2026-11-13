from src.data.labels import SCENARIO_GROUP, decode_index, is_damaged


def test_decode_index_roundtrip():
    for idx in range(17 * 90):
        s, u, g = decode_index(idx)
        assert idx == s * 90 + u * 10 + g
    assert decode_index(1529) == (16, 8, 9)


def test_groups():
    assert len(SCENARIO_GROUP) == 17
    assert is_damaged(0) is False and is_damaged(7) is False
    assert is_damaged(1) is None
    assert is_damaged(5) is True
