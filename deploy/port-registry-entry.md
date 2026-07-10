# Port registry entry — copy row to /opt/shared/port-registry.md

Full allocation (LiveKit, OTEL, memory bridge, Traefik, env vars): **[docs/operations/PORT-REGISTRY.md](../docs/operations/PORT-REGISTRY.md)**.

vps-shared columns: `slug | path | host | ports | notes`

```markdown
| advoi | /opt/advoi | advoi.keyteller.com | PG 127.0.0.1:5438, Redis 127.0.0.1:6382, API 8010, Voice 8011, Web 3000 | Traefik advoi-web, advoi-api, advoi-voice; Shelve ktteam/advoi/staging |
```

## Host port allocation (do not collide)

| Service | Host bind | Internal |
|---------|-----------|----------|
| PostgreSQL | 127.0.0.1:5438 | 5432 |
| Redis | 127.0.0.1:6382 | 6379 |
| advoi-api (dev/staging map) | ADVOI_API_HOST_PORT / ADVOI_API_PORT=8010 | 8000 |
| advoi-voice | ADVOI_VOICE_PORT=8011 | 8080 |
| advoi-web | ADVOI_WEB_PORT=3000 | 3000 |
| advoi-memory-bridge | ADVOI_MEMORY_BRIDGE_PORT=8095 | 8095 |
| livekit | LIVEKIT_HOST_PORT=7880, RTC 7881, UDP 50100–50200 | same |
| otel-collector | 4317 (gRPC), 4318 (HTTP), 8888 (metrics) | same |

Verify uniqueness before deploy:

```bash
ss -tlnp | grep -E '5438|6382|8010|8011|8095|7880|7881|4317|4318'
```
