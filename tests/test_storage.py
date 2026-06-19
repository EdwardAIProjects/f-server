from io import BytesIO

import pytest

from f_server.storage.local import LocalStorage


def test_local_storage_round_trip(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    storage.put("repo/app.apk", BytesIO(b"apk"), "application/octet-stream")

    assert storage.exists("repo/app.apk")
    with storage.open_stream("repo/app.apk") as fp:
        assert fp.read() == b"apk"


def test_local_storage_rejects_traversal(tmp_path) -> None:
    storage = LocalStorage(tmp_path)

    with pytest.raises(ValueError):
        storage.put("../outside", BytesIO(b"x"), "text/plain")
