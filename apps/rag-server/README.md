# rag-server — Personal RAG with Remote MCP

Private knowledge retrieval over Junho's Claude conversations, project docs,
and manual notes. Runs as a Docker Compose service on the always-on laptop,
exposed at `https://rag.6-6ho.com/mcp` through the existing Cloudflare Tunnel,
protected by OAuth 2.1 (PKCE + Dynamic Client Registration). Connected to
Claude.ai as a custom MCP connector.

## Architecture

```
claude.ai  ─OAuth─►  https://rag.6-6ho.com/mcp
                         │
                  Cloudflare Tunnel (jdp-tunnel)
                         │
                         ▼
                    jdp-rag  (FastMCP 3.x + personal_auth)
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         jdp-postgres-1  Voyage  /mnt/host/rag-data
         (pgvector)     (embed)   (bind mount)
```

- **FastMCP** serves the MCP transport and exposes 5 tools.
- **PersonalAuthProvider** (`rag_server/personal_auth.py`, vendored from
  [crumrine/fastmcp-personal-auth](https://github.com/crumrine/fastmcp-personal-auth))
  implements OAuth 2.1 + DCR, restricted to `claude.ai`/`claude.com`/`localhost`
  redirect domains. OAuth state persists in the `rag-oauth-state` volume.
- **pgvector 0.8.2** in the shared `jdp-postgres-1` database under schema `rag`.
- **Voyage `voyage-3-large`** for 1024-dim embeddings (Korean+English).
- **BM25 fallback** via Postgres `tsvector` ensures retrieval works even when
  some chunks fail to embed (rate limits, transient errors).

## Files

```
apps/rag-server/
├── Dockerfile
├── pyproject.toml            fastmcp[auth] + voyageai + psycopg2 + pgvector
├── rag_server/
│   ├── config.py             pydantic-settings (env)
│   ├── db.py                 psycopg2 singleton (pattern from investment-agent)
│   ├── schema.py             idempotent DDL — runs at container startup
│   ├── embedding.py          Voyage wrapper, lazy client, batch embed
│   ├── chunking.py           char-based + turn-based chunking
│   ├── retrieve.py           hybrid vector + BM25 (RRF-merged)
│   ├── mcp_tools.py          the 5 user-facing tool implementations
│   ├── main.py               FastMCP app + tool registration
│   └── personal_auth.py      OAuth provider (vendored, MIT)
├── ingest/
│   ├── common.py             shared upsert/embed helpers
│   ├── secret_scrubber.py    regex-based API-key redaction
│   ├── claude_jsonl.py       Claude Code session JSONL parser
│   ├── markdown.py           .md / plan / project_doc reader
│   └── run.py                CLI entrypoint
└── scripts/
    ├── reembed_missing.py    rate-limit-tolerant embedding backfill
    ├── smoke_search.py       ad-hoc retrieval tests
    └── backup_rag.sh         daily pg_dump of rag.* schema
```

Schema DDL also mirrored at `infra/postgres-init/30_rag.sql` for fresh volume
init — existing Postgres volumes use the runtime path in `schema.py`.

## MCP Tools Exposed

| Tool | Purpose |
|---|---|
| `search(query, limit, source_kind?)` | Hybrid (vector + BM25 RRF) search. Korean or English. |
| `get_document(source_id)` | Fetch full source + all chunks for a matched source. |
| `add_note(content, tags?, title?)` | Save a manual note (kind=`manual_note`). Scrubbed. |
| `list_sources(source_kind?, limit)` | Browse the knowledge base. |
| `delete_note(source_id)` | Remove a `manual_note`. Refuses other kinds. |

## Source Kinds

| Kind | Origin | How to re-ingest |
|---|---|---|
| `claude_session` | Claude Code JSONL dumps rsynced to `/home/junho/rag-data/claude-projects/` | `ingest.run --kind claude_session --glob '.../*/*.jsonl'` |
| `project_doc` | junho-data-platform docs under `/home/junho/rag-data/jdp-docs/` | `ingest.run --kind project_doc --glob '.../*.md'` |
| `plan` | `~/.claude/plans/*.md` (WSL and Windows) staged at `/home/junho/rag-data/plans/` | `ingest.run --kind plan --glob '.../*.md'` |
| `manual_note` | `add_note` MCP tool | via Claude.ai conversation |
| `idea_harness` | reserved, future | TBD |

Ingestion is **idempotent**: `upsert_source` updates by `(kind, origin)` and
`delete_existing_chunks` clears old chunks before re-inserting. Re-running an
ingest refreshes content and metadata without creating duplicates.

## Operations

### Start / stop / restart

```bash
ssh junho@192.168.219.101 \
  "cd ~/junho-data-platform && docker compose -f docker-compose.laptop.yml restart rag-server"
```

### Rebuild after code changes

```bash
# from desktop WSL
rsync -av --delete ~/junho-data-platform/apps/rag-server/ \
  junho@192.168.219.101:~/junho-data-platform/apps/rag-server/
ssh junho@192.168.219.101 \
  "cd ~/junho-data-platform && docker compose -f docker-compose.laptop.yml build rag-server \
   && docker compose -f docker-compose.laptop.yml up -d --force-recreate rag-server"
```

### Check health

```bash
# external
curl https://rag.6-6ho.com/health

# internal container
ssh junho@192.168.219.101 'docker exec jdp-rag curl -s http://localhost:8000/health'

# stats
ssh junho@192.168.219.101 'docker exec jdp-rag python -m ingest.run --stats'
```

### Ingest new content

1. Sync source files from desktop WSL to laptop staging:
   ```bash
   rsync -rtv --include="*/" --include="*.jsonl" --exclude="*" \
     ~/.claude/projects/ junho@192.168.219.101:~/rag-data/claude-projects/
   rsync -rtv ~/junho-data-platform/CLAUDE.md \
     ~/junho-data-platform/.claude/*.md ~/junho-data-platform/docs/*.md \
     junho@192.168.219.101:~/rag-data/jdp-docs/
   rsync -rtv ~/.claude/plans/*.md \
     junho@192.168.219.101:~/rag-data/plans/
   ```
2. Run ingest inside the container:
   ```bash
   # VOYAGE_API_KEY read from host — pass via -e so it's not persisted
   KEY=$(python3 -c "import json; print(json.load(open('/home/junho/junho-data-platform/.claude/.mcp.json'))['mcpServers']['investment-agent']['env']['VOYAGE_API_KEY'])")
   ssh junho@192.168.219.101 "docker exec -e VOYAGE_API_KEY='$KEY' jdp-rag \
     python -m ingest.run --kind claude_session --glob '/mnt/host/rag-data/claude-projects/*/*.jsonl'"
   ```

### Backfill embeddings (after rate limit)

Chunks inserted without embeddings (e.g., during rate-limited bulk ingest or
with `VOYAGE_API_KEY` unset for the speed path) can be filled in later:

```bash
ssh junho@192.168.219.101 "docker exec -d -e VOYAGE_API_KEY='$KEY' -e PYTHONPATH=/app jdp-rag \
  bash -c 'python /app/scripts/reembed_missing.py > /tmp/reembed.log 2>&1'"

# monitor
ssh junho@192.168.219.101 'docker exec jdp-rag tail -f /tmp/reembed.log'
```

Under Voyage free tier (3 RPM / 10K TPM) the script paces itself to stay
within limits and retries on rate-limit errors with exponential backoff.
Expect ~1200 chunks/hour at free tier, ~30K chunks/hour with paid billing.

### Backup

`scripts/backup_rag.sh` dumps the `rag.*` schema to `/home/junho/rag-backups/`
with 7-day retention. Install via laptop crontab:

```
15 4 * * *  /home/junho/junho-data-platform/apps/rag-server/scripts/backup_rag.sh
```

### Monitor reembed progress

```bash
ssh junho@192.168.219.101 'docker exec jdp-rag tail -f /tmp/reembed.log'
# or just check stats periodically
watch -n 60 "ssh junho@192.168.219.101 'docker exec jdp-rag python -m ingest.run --stats'"
```

## Security Model

- **Transport**: HTTPS via Cloudflare Tunnel, cert provisioned by Cloudflare.
- **Auth**: OAuth 2.1 PKCE + DCR. Only `claude.ai` / `claude.com` / `localhost`
  redirect URIs can complete the authorization flow (`allowed_redirect_domains`
  in `personal_auth.py`).
- **Rate/URL obscurity**: The final attack surface reduces to "someone else
  knows the URL AND has a claude.ai account." Keep `rag.6-6ho.com` private.
- **Secret scrubbing**: Ingestion regex-redacts API keys (Voyage, Anthropic,
  OpenAI, GitHub, AWS, JWT, long hex). See `ingest/secret_scrubber.py`.
- **Token storage**: OAuth access tokens are opaque random bytes stored in the
  `rag-oauth-state` volume. Access token TTL 30 days default, refresh
  indefinite. Revoke via claude.ai Settings → Integrations.
- **Privileged tools**: `delete_note` refuses to delete non-`manual_note`
  sources (project_doc / plan / claude_session can only be wiped via
  `delete_existing_chunks` during re-ingestion).

## Environment Variables

Required in `.env` (or `environment:` block of docker-compose):

| var | required | default | purpose |
|---|---|---|---|
| `DB_HOST` | no | `postgres` | Postgres host |
| `DB_PORT` | no | `5432` | |
| `DB_NAME` | no | `app` | |
| `DB_USER` | no | `postgres` | |
| `DB_PASSWORD` | **yes** | `postgres` | |
| `VOYAGE_API_KEY` | **yes (for embedding)** | — | leave unset during bulk ingest to skip embedding |
| `VOYAGE_MODEL` | no | `voyage-3-large` | |
| `VOYAGE_DIM` | no | `1024` | must match pgvector column dim |
| `OAUTH_ISSUER` | no | `https://rag.6-6ho.com` | public-facing URL |
| `RAG_JWT_SIGNING_KEY` | no | — | reserved (personal_auth uses opaque tokens) |
| `RAG_LOGIN_TOKEN` | no | — | reserved for future password gate |
| `RAG_ALLOWED_USER_SUB` | no | `junho` | reserved |

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `/health` returns 502 | tunnel routes to container but server still booting | wait 10–20s after `up -d` |
| `/mcp` returns 401 | missing/expired Bearer token | re-register connector in claude.ai |
| `/authorize` 400 invalid client | client_id mismatch | claude.ai will retry DCR; hard-reset by removing and re-adding |
| `/authorize` 302 access_denied | redirect URI not in allowlist | check `personal_auth.py:allowed_redirect_domains` |
| `chunks_embedded` never grows | reembed process dead or rate-limited | `docker exec jdp-rag cat /tmp/reembed.log`, restart with fresh key |
| Voyage "payment not added" | free tier rate limit | either add billing at dashboard.voyageai.com or let the reembed loop run overnight |
| Ingest OOM | `claude_jsonl` holding whole file | reduce `BATCH_SIZE`, split large JSONLs |

## References

- plan: `C:\Users\Junho\.claude\plans\personal-rag-mcp.md`
- related: `apps/investment-agent/` (same Voyage+pgvector pattern, stdio MCP)
- external: [FastMCP](https://gofastmcp.com/), [MCP Spec](https://modelcontextprotocol.io/),
  [Claude Custom Connectors](https://support.claude.com/en/articles/11503834)
