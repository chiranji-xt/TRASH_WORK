# Database setup — use Alembic (these scripts are superseded)

Canonical workflow (from `backend-database/` with `.env` configured):

```bash
pip install -r requirements.txt
alembic upgrade head        # creates PostGIS extension + garbage_reports table
```

The one-off scripts below are kept for history only — do not use for new setups:

| Script | Replaced by |
|---|---|
| `init_db.py` | `alembic upgrade head` |
| `migrate_db.py` (detections column) | revision `0001_initial` |
| `add_status_column_migration.py` | revision `0001_initial` |
| `add_boxed_column_migration.py` | revision `0001_initial` |

Note: `migrate_db.py` previously contained a hardcoded dev password.
That password has been revoked — set `DB_PASSWORD` in `.env` (see `.env.example`).
