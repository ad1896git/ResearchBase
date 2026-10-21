#!/usr/bin/env bash
set -euo pipefail

image='postgres:18-alpine'
container_name='researchbase-pr2-02-review-postgres'
review_tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/researchbase-pr2-02-review.XXXXXX")"
container_created=0

cleanup() {
  if [ "$container_created" -eq 1 ]; then
    docker rm --force "$container_name" >/dev/null 2>&1 || true
  fi
  rm -rf "$review_tmp_dir"
}
trap cleanup EXIT

if docker container inspect "$container_name" >/dev/null 2>&1; then
  printf 'Container %s already exists; remove it before reviewer setup.\n' "$container_name" >&2
  exit 1
fi

if ! docker image inspect "$image" >/dev/null 2>&1; then
  printf '%s\n' 'PostgreSQL 18 image is not local; pulling with an isolated Docker config.'
  mkdir "$review_tmp_dir/docker-config"
  printf '%s\n' '{"auths":{}}' > "$review_tmp_dir/docker-config/config.json"
  docker_context="$(docker context show)"
  docker context export "$docker_context" "$review_tmp_dir/docker-context.tar" >/dev/null
  DOCKER_CONFIG="$review_tmp_dir/docker-config" docker context import \
    "$docker_context" "$review_tmp_dir/docker-context.tar" >/dev/null
  DOCKER_CONFIG="$review_tmp_dir/docker-config" DOCKER_CONTEXT="$docker_context" \
    docker pull "$image"
fi

docker run --detach \
  --name "$container_name" \
  --env POSTGRES_USER=researchbase \
  --env POSTGRES_PASSWORD=researchbase_test \
  --env POSTGRES_DB=researchbase_test \
  --publish 127.0.0.1::5432 \
  "$image" >/dev/null
container_created=1

ready=0
for attempt in $(seq 1 60); do
  if docker exec "$container_name" pg_isready -U researchbase -d researchbase_test >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  printf 'PostgreSQL did not become ready in time.\n' >&2
  docker logs "$container_name" >&2 || true
  exit 1
fi

published_port="$(docker port "$container_name" 5432/tcp)"
host_port="${published_port##*:}"
export DATABASE_URL="postgresql+psycopg://researchbase:researchbase_test@127.0.0.1:${host_port}/researchbase_test"
export UV_CACHE_DIR="$review_tmp_dir/uv-cache"

docker exec "$container_name" psql -U researchbase -d researchbase_test -Atc 'SHOW server_version'
uv run alembic upgrade 0018_current_pointer_same_parent_integrity
uv run alembic current

uv run pytest -o addopts='' \
  tests/integration/phase2/test_pr2_02_source_version_migration.py \
  tests/integration/phase2/test_pr2_02_gov_application.py \
  tests/integration/phase2/test_pr2_02_gov_migration.py \
  tests/integration/phase2/test_pr2_01_source_identity.py

uv run pytest -o addopts='' -q
