from isi_util import list_util

li = ["a", "b", "c"]


def test_find_index():
    assert list_util.find_index(li, lambda x: x == "b") == 1


def test_find_index_non_existent():
    assert list_util.find_index(li, lambda x: x == "d") == -1


def test_find():
    assert list_util.find(li, lambda x: x == "b") == "b"


def test_find_non_existent():
    assert list_util.find(li, lambda x: x == "d") is None
