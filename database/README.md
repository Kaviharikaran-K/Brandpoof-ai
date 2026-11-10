# Database

This folder holds PostgreSQL bootstrap material for Docker Compose.

- `init.sql` — executed once when the Postgres volume is first created.

The application schema itself is managed by Alembic in `backend/alembic/`.
Run `python -m alembic upgrade head` from `backend/` after starting Postgres.

Connection string (see `backend/.env.example`):

```
DATABASE_URL=postgresql+asyncpg://brandproof:brandproof@localhost:5432/brandproof
```
