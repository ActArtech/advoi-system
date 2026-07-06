# Port registry entry — copy row to /opt/shared/port-registry.md

```markdown
| advoi | /opt/advoi | advoi.keyteller.com | PG 127.0.0.1:5438, Redis 127.0.0.1:6382 | Traefik advoi-web, advoi-api; Shelve ktteam/advoi/staging |
```

## Host port allocation (do not collide)

| Service | Host bind | Internal |
|---------|-----------|----------|
| PostgreSQL | 127.0.0.1:5438 | 5432 |
| Redis | 127.0.0.1:6382 | 6379 |
| advoi-api (dev) | ADVOI_API_PORT=8010 | 8000 |
| advoi-voice (dev) | ADVOI_VOICE_PORT=8011 | 8080 |

Verify uniqueness before deploy:

```bash
ss -tlnp | grep -E '5438|6382|8010|8011'
```