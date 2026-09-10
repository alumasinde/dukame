# DukaMe database migrations

Alembic is the only supported mechanism for application schema changes.

## Development

Create a migration after changing SQLAlchemy models:

```bash
alembic revision --autogenerate -m "describe the schema change"
```

Review the generated migration before applying it:

```bash
alembic upgrade head
```

Check the current database revision:

```bash
alembic current
```

Check pending migrations:

```bash
alembic check
```

## Rules

- Commit the migration with the model change.
- Never edit an already-applied migration.
- Never use `Base.metadata.create_all()` for application startup or production deployment.
- Do not use HeidiSQL to modify application schema during normal development.
- Prefer backward-compatible expand, migrate, contract changes for production deployments.
- Test the complete migration chain against a clean database in CI.
