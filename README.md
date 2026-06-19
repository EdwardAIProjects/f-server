# f-server

`f-server` is a self-hosted F-Droid-compatible repository service for many independent Android projects. CI jobs upload APKs with scoped API keys; the server verifies package scope, pins APK signing certificates on first upload, stores binaries, and republishes F-Droid index files.

## Quick start

```sh
uv sync
uv run f-server init --keystore ./repo-keystore.p12
uv run f-server keys create --label first-ci --scope '*'
uv run uvicorn f_server.main:app --reload
```

The admin panel is at `http://localhost:8000/admin`, the public repository is under `http://localhost:8000/repo`, and health checks use `GET /health`.

## Configuration

Configuration is read from `config.yaml`, `.env`, and `FS_`-prefixed environment variables. Nested values use `__`, for example `FS_STORAGE__BACKEND=s3`.

```yaml
database_url: sqlite:///./f-server.db
storage:
  backend: local
  local_path: ./data/storage
  # for S3/min.io, endpoint is used by the server and public_base_url is used in presigned redirects
  # endpoint: http://minio:9000
  # public_base_url: http://127.0.0.1:9000
repo:
  name: f-server
  description: Private F-Droid repository
  url: http://localhost:8000/repo
  keystore_path: ./repo-keystore.p12
  keystore_pass: change-me
  key_alias: f-server
  key_pass: change-me
admin_auth:
  mode: none
  session_secret: change-me
download_auth:
  mode: none
uploads:
  onboarding: tofu_scoped
```

Repo signing requires `keytool`, `jarsigner`, and `apksigner` on the host or container image.

## Upload security

Every upload must pass both checks:

- API key scope: the bearer token must allow the APK package name, using exact names or globs such as `com.example.*`.
- APK signing pin: the first upload for a new package pins its signing certificate fingerprint. Later uploads must match a pinned fingerprint unless an admin adds a rotated key.

The Android signing key is never uploaded to f-server.

## CI integration

See [docs/pushing-to-f-server.md](docs/pushing-to-f-server.md) for the full upload contract, GitHub Actions job, curl snippet, and error remediation table.

## Podman deployment

```sh
cp .env.example .env
podman compose up --build
```

Generate the repo signing keystore in the app volume before publishing APKs:

```sh
podman compose exec f-server f-server init \
  --keystore /var/lib/f-server/keystore/repo-keystore.p12 \
  --alias f-server \
  --password change-me
```

For rootless Podman bind mounts, prefer named volumes. If binding host directories for keystores or local storage, use SELinux relabeling such as `:Z` or keep user IDs aligned with `--userns=keep-id`.
