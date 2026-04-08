# Peppermint.sh Integration — SRE Incident Agent

## Overview

[Peppermint](https://peppermint.sh/) is an open-source, self-hosted ticket management and helpdesk system.

## Structure

```
infrastructure/ticketing/
├── docker-compose.yml    # Peppermint + PostgreSQL
└── .env.example          # Environment variables template
```

## Quickstart

```bash
# 1. Copy environment variables
cp .env.example .env

# 2. Start services
docker compose up -d

# 3. Access Peppermint
# Web UI: http://localhost:3001
# API:    http://localhost:5003
```

## API Integration

Peppermint exposes a REST API at `http://localhost:5003/api/`.
The backend integration should use this endpoint to:
- Create tickets on incident triage
- Query ticket status
- Close tickets on resolution

## Ports

| Service | Host Port |
|---------|-----------|
| Peppermint Web | 3001 |
| Peppermint API | 5003 |
| PostgreSQL | 5433 |
