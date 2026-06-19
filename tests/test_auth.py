from f_server.auth.api_keys import package_allowed
from f_server.models import ApiKey


def test_package_scope_globs() -> None:
    key = ApiKey(
        label="ci",
        hashed_secret="hash",
        allowed_package_globs=["com.example.*", "org.one.app"],
        permissions=["upload"],
    )

    assert package_allowed(key, "com.example.app")
    assert package_allowed(key, "org.one.app")
    assert not package_allowed(key, "net.other.app")
