from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from f_server.config import Settings
from f_server.db import Base
from f_server.fdroid.index import build_index_payload, write_unsigned_indexes
from f_server.models import AllowedSigningKey, App, Version


def test_build_index_payload_contains_versions(tmp_path) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        app = App(package_name="com.example.app", name="Example", summary="Summary", categories=["Tools"])
        session.add(app)
        session.flush()
        session.add(AllowedSigningKey(package_name=app.package_name, sha256_fingerprint="a" * 64))
        session.add(
            Version(
                package_name=app.package_name,
                version_name="1.0",
                version_code=1,
                apk_name="com.example.app_1_aaaaaaa.apk",
                storage_key="repo/com.example.app_1_aaaaaaa.apk",
                size=3,
                sha256_hash="b" * 64,
                min_sdk=23,
                target_sdk=35,
                max_sdk=None,
                nativecode=[],
                permissions=["android.permission.INTERNET"],
                signer_fingerprint="a" * 64,
                release_channel="release",
            )
        )
        session.commit()

        payload = build_index_payload(session, Settings())
        package = payload["packages"]["com.example.app"]
        assert package["metadata"]["name"]["en-US"] == "Example"
        assert package["versions"]["b" * 64]["manifest"]["versionCode"] == 1

        files = write_unsigned_indexes(session, Settings(), tmp_path / "repo")
        assert {path.name for path in files} == {"entry.json", "index-v1.json", "index-v2.json"}
