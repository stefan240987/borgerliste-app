#!/usr/bin/env bash
# Opret git commit + tag for nuværende APP_VERSION (release-snapshot).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PUSH=false
if [[ "${1:-}" == "--push" ]]; then
  PUSH=true
elif [[ -n "${1:-}" ]]; then
  echo "Brug: $0 [--push]" >&2
  exit 1
fi

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "FEJL: Ikke et git-repo." >&2
  exit 1
fi

if [[ -z "$(git config user.email 2>/dev/null)" || -z "$(git config user.name 2>/dev/null)" ]]; then
  echo "FEJL: Git brugeridentitet mangler (user.name / user.email)." >&2
  exit 1
fi

VERSION="$(python3 -c "import sys; sys.path.insert(0, '.'); from config import APP_VERSION; print(APP_VERSION)")"
TAG="v${VERSION}"

if ! grep -qF "## [${VERSION}]" CHANGELOG.md; then
  echo "FEJL: CHANGELOG.md mangler sektion ## [${VERSION}]" >&2
  exit 1
fi

if git rev-parse --verify "refs/tags/${TAG}" >/dev/null 2>&1; then
  echo "FEJL: Git-tag ${TAG} findes allerede ($(git rev-parse --short "${TAG}"))." >&2
  exit 1
fi

git add -u -- \
  app.py auth.py config.py matching.py storage.py data_io.py i18n.py licensing.py \
  requirements.txt Dockerfile CHANGELOG.md README.md SERVER_DEPLOYMENT.md \
  test_app_modules.py setup_and_run.py docker-entrypoint.sh \
  .env.example .gitignore .dockerignore \
  "Start Borgerliste.bat" "Start Borgerliste.command" \
  docker-compose.yml docker-compose.ghcr.yml

git add -- \
  scripts/ ui/ assets/ .github/ .cursor/rules/ \
  .streamlit/config.toml .streamlit/secrets.toml.example 2>/dev/null || true

if git diff --cached --quiet; then
  echo "FEJL: Intet at committe." >&2
  exit 1
fi

TITLE="$(grep -m1 "^## \\[${VERSION}\\]" CHANGELOG.md | sed "s/^## \\[${VERSION}\\] — //")"
COMMIT_MSG="Release ${TAG}: ${TITLE}"

git commit -m "${COMMIT_MSG}"
git tag "${TAG}"

echo "✓ Snapshot oprettet: $(git rev-parse --short HEAD) + tag ${TAG}"

if [[ "${PUSH}" == true ]]; then
  BRANCH="$(git branch --show-current)"
  git push origin "HEAD:${BRANCH}"
  git push origin "${TAG}"
  echo "✓ Push'et branch og tag til origin"
fi
