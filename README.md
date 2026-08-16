# simple-social

A FastAPI social platform — feed, posts, comments, likes, follows, and profiles — served as HTML with Jinja2 + HTMX, backed by PostgreSQL. It's a complete delivery stack in one repo: application code, tests, CI validation, container security scanning, and the Kubernetes manifests used to actually run it.

It's also the example workload for a separate self-service GitOps platform on EKS — see [Related repos](#related-repos). Nothing in this repo is platform-specific; any app could onboard to that platform the same way this one did.

## What the project does

Users can sign up, log in, and log out; manage their profile; create and delete posts; like and comment; follow and unfollow other users; upload media via presigned S3 URLs; and browse a personalized feed and profile pages.

The UI is server-rendered HTML (Jinja2), with HTMX handling partial updates instead of a separate frontend framework. Hyperscript covers the interactions HTMX alone doesn't fit well — most notably the presigned S3 upload flow (client requests a presigned URL, then `PUT`s the file straight to S3), plus other small client-side state/UI behavior — without reaching for a general-purpose JS framework.

## Architecture at a glance

1. **Application layer** — FastAPI app in `code/`: async SQLAlchemy models and data access, Jinja2 + HTMX templates, scheduled jobs, object cleanup logic.
2. **CI/CD layer** — PR lint/test validation, container build + Trivy vulnerability scanning, ECR push, automated image-tag bump PR against the `gitops` repo.
3. **Runtime deployment layer** — Kustomize-based Kubernetes manifests: ingress, service, deployment, namespace, monitoring, and AWS Secrets Manager / Parameter Store integration via External Secrets.

## Tech stack

Python 3.12+, FastAPI, SQLAlchemy 2 (async), PostgreSQL, `fastapi-users`, Jinja2 + HTMX + Hyperscript, Alembic, APScheduler, boto3, `prometheus-fastapi-instrumentator`, GitHub Actions, Kubernetes + Kustomize.

## Repository structure

```text
.
├── code/
│   ├── api/
│   │   ├── dependency.py          # auth/session setup and FastAPI Users integration
│   │   ├── super_user.py          # superuser-related endpoints
│   │   └── route/
│   │       ├── auth.py            # login/register routes
│   │       ├── comments.py        # create/delete comments
│   │       ├── likes.py           # like/unlike posts
│   │       ├── posts.py           # feed, post pages, and post creation
│   │       ├── uploads.py         # presigned upload URLs
│   │       └── users.py           # profile, follow, settings routes
│   ├── core/
│   │   ├── config.py              # settings and environment loading
│   │   ├── db.py                  # async SQLAlchemy engine/session
│   │   └── storage.py             # S3 client and signed URL helpers
│   ├── templates/
│   │   ├── base.html              # base layout and global nav
│   │   ├── pages/
│   │   └── partials/
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── test/
│   │   ├── conftest.py            # SAVEPOINT-isolated Postgres fixtures, multi-user clients
│   │   └── route/
│   ├── scripts/
│   │   ├── create_user.py         # idempotent first-superuser bootstrap
│   │   └── populate_db.py         # optional demo data seeding
│   ├── main.py                    # FastAPI app bootstrap and route registration
│   ├── crud.py                    # business logic for posts, comments, likes, follows
│   ├── models.py                  # ORM models
│   ├── schemas.py                 # request and response models
│   ├── middleware.py              # structured logging middleware
│   ├── logging_config.py          # logger setup
│   ├── jobs.py                    # scheduled jobs registration
│   ├── metrics.py                 # Prometheus instrumentation
│   ├── utils.py                   # user creation + orphan cleanup helpers
│   ├── exception.py                # custom database exceptions
│   ├── Dockerfile                 # multi-stage app image build
│   └── pyproject.toml             # dependencies and tooling config
├── .github/
│   └── workflows/
│       ├── pr-scan.yaml           # PR lint/test workflow
│       └── build-push.yaml        # build + Trivy + ECR push + gitops PR workflow
└── k8s/
    ├── base/
    │   ├── namespace.yaml
    │   ├── serviceaccount.yaml
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   ├── ingress.yaml
    │   ├── create-first-superuser-job.yaml
    │   ├── db-migrate-job.yaml
    │   └── kustomization.yaml
    └── overlays/
        └── dev/
            ├── kustomization.yaml
            ├── configmap.yaml
            ├── ingress-patch.yaml
            ├── servicemonitor.yaml
            ├── external-secrets.yaml
            ├── external-secrets-store-sm.yaml
            └── external-secrets-store-ssm.yaml
```

## How the app works

The entrypoint is `code/main.py`. At startup it creates the FastAPI app, configures structured logging, sets up the scheduler for periodic jobs, mounts static files, registers routers for auth/users/posts/comments/likes/uploads, enables pagination, and exposes `/healthz` and Prometheus metrics at `/metrics`.

Main routes:

| Route | Purpose |
|---|---|
| `/` | Redirect logic for signed-in vs. signed-out users |
| `/feed` | User feed page |
| `/users/profile/{user_id}` | User profile |
| `/posts` | Create a post |
| `/posts/{post_id}` | Fetch one post |
| `/posts/{post_id}/comments` | Add comments |
| `/posts/{post_id}/like` | Toggle likes |
| `/presign` | Get a presigned S3 upload URL |
| `/auth/cookie/login`, `/auth/cookie/logout` | Cookie auth flow |

## Configuration and environment

Configuration is read via `pydantic-settings` from `code/.env`:

```env
APP_NAME=Simple Social
DEBUG=False
LOG_LEVEL=INFO
LOG_JSON_FORMAT=True
SECRET_KEY=replace-with-a-long-random-secret
COOKIE_MAX_AGE=604800

FIRST_SUPERUSER_EMAIL=admin@example.com
FIRST_SUPERUSER_PASSWORD=password_123
FIRST_SUPERUSER_USERNAME=admin
FIRST_SUPERUSER_DISPLAY_NAME=Admin

POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=simple_social

REGION_NAME=us-east-1
BUCKET_NAME=simple-social
ENDPOINT_URL=http://localhost:9000
ACCESS_KEY_ID=your-access-key
SECRET_ACCESS_KEY=your-secret-key
PUBLIC_URL=https://example.com
ENABLE_METRICS=True
```

- `POSTGRES_*` build the async database URL.
- `BUCKET_NAME` and region settings configure S3-compatible upload storage.
- `FIRST_SUPERUSER_*` are consumed by the admin bootstrap job.
- Login sessions are cookie-based, backed by a DB-stored access token — not JWT. `SECRET_KEY` is used by `fastapi-users` for the tokens it does sign as JWTs (e.g. email verification), not for the session itself.

## Local development

**Prerequisites:** Python 3.12+, a running PostgreSQL instance, S3-compatible storage (or a local mock), `uv`.

```bash
cd code
uv sync --dev
uv run alembic upgrade head
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Then visit `/`, `/docs`, and `/healthz`.

Bootstrap the first admin user, if needed:

```bash
uv run python -m scripts.create_user
```

## Testing

```bash
uv run ruff check .
uv run python -m pytest -v
```

The suite runs against a real PostgreSQL database, not SQLite — the same engine used in production — with SAVEPOINT-based per-test transaction isolation. Application code can `commit()` internally (as `fastapi-users` does on user creation) without leaking state between tests: only the inner savepoint is torn down after each test, and the outer transaction is always rolled back. Coverage includes auth, feed/profile behavior, comment/like flows, and — deliberately, since this is where real bugs hide — cross-user permission boundaries (a user cannot edit, delete, or otherwise act on another user's resources).

## CI/CD

**PR checks** (`.github/workflows/pr-scan.yaml`) — on every pull request: install deps with `uv`, `ruff check`, then the full pytest suite against a throwaway PostgreSQL service container spun up for that run only.

**Build and deploy** (`.github/workflows/build-push.yaml`) — on push to `main`:

1. Builds the app image from `code/` and tags it with the short git SHA — the tag that actually gets deployed is always traceable back to an exact commit, never a floating `latest`.
2. Authenticates to AWS via OIDC (no long-lived credentials in the repo) and pushes to ECR, using an IAM role scoped to ECR push only — kept separate from the platform's Terraform provisioning role, so a compromised app build can't reach the rest of the AWS account.
3. Scans the built image with Trivy, gated on `CRITICAL`/`HIGH` findings with `--ignore-unfixed`. The two Python-level findings that do show up (`msgpack`, `setuptools`) were traced by scanning the bare upstream `python:3.13-slim-trixie` base image directly — they're vendored inside `pip`'s own bundled dependencies, not anything installed by this app, and are documented as such in `.trivyignore` rather than silently suppressed.
4. Opens an automated pull request against the `gitops` repo, bumping this app's image tag in `k8s/overlays/dev/kustomization.yaml` via `yq`. Argo CD picks up the change once that PR is merged — this repo never pushes to the cluster directly.

## Kubernetes components

Runtime config lives in `k8s/`, split into a base layer and a dev overlay, deployed by the `gitops` repo's `simple-social` Argo CD `Application`, which points straight at this repo's `k8s/overlays/dev` path.

**Base (`k8s/base/`):** `namespace.yaml`, `serviceaccount.yaml`; `deployment.yaml` (2 replicas, port 80, readiness/liveness on `/healthz`, resource limits, Prometheus scrape annotations); `service.yaml` (ClusterIP); `ingress.yaml`; `db-migrate-job.yaml` and `create-first-superuser-job.yaml` (both run as Argo CD `PreSync` hooks, migration first); `kustomization.yaml`.

**Dev overlay (`k8s/overlays/dev/`):** `kustomization.yaml` (adds dev resources, sets the image tag CI bumps); `configmap.yaml` (non-secret runtime config — app name, log settings, cookie lifetime, bucket/region, metrics toggle); `servicemonitor.yaml` (Prometheus scraping of `/metrics`); `external-secrets.yaml` plus `external-secrets-store-sm.yaml` / `external-secrets-store-ssm.yaml` (this app's own `SecretStore`s against Secrets Manager and Parameter Store, and the `ExternalSecret`s that consume them — self-contained, not dependent on anything in the platform repos); `ingress-patch.yaml`.

## Deployment flow

1. Base manifests and the dev overlay are assembled with Kustomize.
2. External Secrets syncs AWS-managed secrets into the cluster.
3. The DB migration job runs (`PreSync`) before the app is considered ready.
4. The first-superuser bootstrap job runs (`PreSync`, after migrations).
5. The app deployment starts and serves traffic.
6. Prometheus scrapes `/metrics` via the `ServiceMonitor`.

Running migrations and superuser creation as separate `PreSync` jobs — rather than on app startup — means they happen exactly once per rollout, not once per replica, and a failure there blocks the rest of the sync instead of leaving pods crash-looping against a schema that isn't ready.

## Docker

Multi-stage build (`code/Dockerfile`) on `python:3.13-slim-trixie`, dependencies installed with `uv`. The final image only contains the built virtual environment and app code — `uv.lock`/`pyproject.toml` aren't copied into the runtime stage, so the full dev-dependency graph never shows up in image scans or the shipped image. Runs as:

```bash
uvicorn main:app --host 0.0.0.0 --port 80
```

## Feature summary

**Social** — personalized feed, profiles, follow/follower relationships, post creation/deletion, comments, likes.
**Auth** — cookie-based sessions, registration, superuser access with elevated permissions (e.g. visibility into other users' emails) not available to regular accounts.
**Operational** — Prometheus metrics, structured logging, S3-compatible uploads via presigned URLs, orphaned-object cleanup jobs, Kubernetes-native deployment.

## Related repos

- [`infra`](https://github.com/Ishihab/infra) — Terraform: VPC, EKS, RDS, ECR, IAM/Pod Identity, Argo CD bootstrap
- [`gitops`](https://github.com/Ishihab/gitops) — Argo CD app-of-apps config; `argocd/applications/simple-social.yaml` is what deploys this repo

## Maintainer notes

Most important files to know: `code/main.py` (app + routing), `code/crud.py` (data operations), `code/models.py` (schema), `code/templates/` (UI), `code/core/config.py` (settings), `.github/workflows/pr-scan.yaml` and `build-push.yaml` (CI/CD), `k8s/` (runtime deployment and monitoring).
