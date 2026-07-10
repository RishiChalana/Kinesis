#!/bin/sh
# Waits for the backend image, then verifies the containerized app end-to-end.
# Not committed as a test dependency — a one-off Phase 10 verification helper.
set -u
cd "$(dirname "$0")/.."

echo "[1/5] waiting for kinesis-backend image..."
until docker images -q kinesis-backend | grep -q .; do sleep 10; done
echo "      image ready: $(docker images kinesis-backend --format '{{.Size}}')"

echo "[2/5] standalone 'docker run' -> /docs should load (no DB needed)..."
docker rm -f ktest >/dev/null 2>&1
docker run -d --name ktest -p 8010:8000 \
  -e DATABASE_URL=postgresql://u:p@localhost/db -e SECRET_KEY=test kinesis-backend >/dev/null
for i in $(seq 1 30); do curl -s http://localhost:8010/docs >/dev/null 2>&1 && break; sleep 2; done
echo "      standalone /docs: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8010/docs)"
echo "      standalone / :     $(curl -s http://localhost:8010/ )"
docker rm -f ktest >/dev/null 2>&1

echo "[3/5] docker compose up --build (backend migrates, then serves)..."
docker compose up --build -d
echo "      waiting for backend /health..."
for i in $(seq 1 90); do curl -s http://localhost:8000/health >/dev/null 2>&1 && break; sleep 3; done
echo "      compose /health: $(curl -s http://localhost:8000/health)"
echo "      compose /docs:   $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/docs)"

echo "[4/5] end-to-end REST via the containerized stack..."
echo "      register: $(curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8000/auth/register -H 'Content-Type: application/json' -d '{\"name\":\"Docker\",\"email\":\"dockertest@example.com\",\"password\":\"pw12345\"}')"
TOK=$(curl -s -X POST http://localhost:8000/auth/login -H 'Content-Type: application/json' -d '{"email":"dockertest@example.com","password":"pw12345"}' | sed 's/.*"access_token":"\([^"]*\)".*/\1/')
echo "      login token (first 20): $(echo "$TOK" | cut -c1-20)"
echo "      /users/me: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/users/me -H "Authorization: Bearer $TOK")"
echo "      frontend :80 -> $(curl -s -o /dev/null -w '%{http_code}' http://localhost/) (index.html served by nginx)"

echo "[5/5] services status + teardown..."
docker compose ps --format '      {{.Service}}: {{.Status}}'
docker compose down
echo "DONE"
