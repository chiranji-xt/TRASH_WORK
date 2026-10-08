import os

_admin = None
_db = None
_configured = False


def _init_if_needed():
    global _admin, _db, _configured
    if _admin is not None:
        return
    try:
        import firebase_admin
        from firebase_admin import credentials, db

        service_key_path = os.environ.get(
            "FIREBASE_SERVICE_ACCOUNT",
            os.path.join(os.path.dirname(__file__), "firebase_service_account.json"),
        )
        database_url = os.environ.get("FIREBASE_DB_URL")

        if service_key_path and os.path.exists(service_key_path) and database_url:
            cred = credentials.Certificate(service_key_path)
            firebase_admin.initialize_app(cred, {"databaseURL": database_url})
            _admin = firebase_admin
            _db = db
            _configured = True
        else:
            _admin = None
            _db = None
            _configured = False
    except Exception:
        _admin = None
        _db = None
        _configured = False


def get_db():
    _init_if_needed()
    return _db


def is_configured():
    _init_if_needed()
    return _configured
