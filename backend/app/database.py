"""
Database — MongoDB & SQLite
===========================
Supports both MongoDB (production) and SQLite (test/dev).
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global collection references (populated at startup by init_database)
# ---------------------------------------------------------------------------
users_collection = None
sessions_collection = None

SQLITE_DB_PATH = "interview.sqlite"


# ═══════════════════════════════════════════════════════════════════════════
#  Shared helpers
# ═══════════════════════════════════════════════════════════════════════════

class _InsertOneResult:
    """Wraps an inserted document ID so callers can do ``result.inserted_id``."""
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


# ═══════════════════════════════════════════════════════════════════════════
#  Async Cursor Interface
# ═══════════════════════════════════════════════════════════════════════════

class _AsyncCursor:
    """Interface for async cursors."""
    async def to_list(self, length: int = 100) -> List[Dict]:
        raise NotImplementedError()

    def sort(self, key: str, direction: int = 1) -> "_AsyncCursor":
        raise NotImplementedError()


# ═══════════════════════════════════════════════════════════════════════════
#  SQLite Implementation
# ═══════════════════════════════════════════════════════════════════════════

class _SQLiteAsyncFind(_AsyncCursor):
    def __init__(self, collection: "SQLiteCollection", query: Dict):
        self._collection = collection
        self._query = query
        self._sort_key: Optional[str] = None
        self._sort_dir: int = 1

    def sort(self, key: str, direction: int = 1):
        self._sort_key = key
        self._sort_dir = direction
        return self

    async def to_list(self, length: int = 100) -> List[Dict]:
        docs = await self._collection._find_all(self._query)
        if self._sort_key:
            docs.sort(
                key=lambda d: d.get(self._sort_key) or "",
                reverse=(self._sort_dir == -1),
            )
        return docs[:length]


class SQLiteCollection:
    _INDEX_COLS = ("user_id", "email", "username", "status", "role")

    def __init__(self, name: str, db_path: str = SQLITE_DB_PATH):
        self.name = name
        self.db_path = db_path
        self._table_ready = False

    async def _ensure_table(self):
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                f'CREATE TABLE IF NOT EXISTS [{self.name}] '
                f'(_id TEXT PRIMARY KEY, data TEXT NOT NULL)'
            )
            for col in self._INDEX_COLS:
                try:
                    await conn.execute(f'ALTER TABLE [{self.name}] ADD COLUMN {col} TEXT DEFAULT NULL')
                except Exception:
                    pass
                try:
                    await conn.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.name}_{col} ON [{self.name}] ({col})')
                except Exception:
                    pass
            await conn.commit()
        self._table_ready = True

    async def _auto_ensure(self):
        if not self._table_ready: await self._ensure_table()

    @staticmethod
    def _encode(doc: Dict) -> str:
        def default(o):
            if isinstance(o, datetime): return {"__dt__": o.isoformat()}
            raise TypeError(type(o))
        return json.dumps(doc, default=default)

    @staticmethod
    def _decode(text: str) -> Dict:
        def hook(o):
            if "__dt__" in o: return datetime.fromisoformat(o["__dt__"])
            return o
        return json.loads(text, object_hook=hook)

    @staticmethod
    def _match(doc: Dict, query: Dict) -> bool:
        for k, v in query.items():
            doc_val = doc.get(k)
            if isinstance(v, dict):
                if "$ne" in v and str(doc_val) == str(v["$ne"]): return False
                continue
            if k == "_id":
                if str(doc.get("_id", "")) != str(v): return False
            elif doc_val != v: return False
        return True

    async def find_one(self, query: Dict) -> Optional[Dict]:
        await self._auto_ensure()
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as conn:
            if "_id" in query and len(query) == 1:
                cur = await conn.execute(f'SELECT data FROM [{self.name}] WHERE _id = ?', (str(query["_id"]),))
                row = await cur.fetchone()
                return self._decode(row[0]) if row else None
            
            idx_keys = [k for k in query if k in self._INDEX_COLS and not isinstance(query[k], dict)]
            if idx_keys and len(query) == len(idx_keys):
                where = " AND ".join(f"{k} = ?" for k in idx_keys)
                cur = await conn.execute(f'SELECT data FROM [{self.name}] WHERE {where} LIMIT 1', [query[k] for k in idx_keys])
                row = await cur.fetchone()
                return self._decode(row[0]) if row else None

            cur = await conn.execute(f'SELECT data FROM [{self.name}]')
            rows = await cur.fetchall()
            for (blob,) in rows:
                doc = self._decode(blob)
                if self._match(doc, query): return doc
            return None

    async def insert_one(self, doc: Dict) -> _InsertOneResult:
        await self._auto_ensure()
        import aiosqlite
        if "_id" not in doc: doc["_id"] = uuid.uuid4().hex[:24]
        doc_id = str(doc["_id"])
        idx_vals = {col: doc.get(col) for col in self._INDEX_COLS if doc.get(col) is not None}
        cols = ", ".join(["_id", "data"] + list(idx_vals.keys()))
        ph = ", ".join(["?"] * (2 + len(idx_vals)))
        vals = [doc_id, self._encode(doc)] + list(idx_vals.values())
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(f'INSERT INTO [{self.name}] ({cols}) VALUES ({ph})', vals)
            await conn.commit()
        return _InsertOneResult(doc_id)

    async def update_one(self, query: Dict, update: Dict):
        await self._auto_ensure()
        import aiosqlite
        doc = await self.find_one(query)
        if doc is None: return
        if "$set" in update:
            for k, v in update["$set"].items(): doc[k] = v
        doc_id = str(doc["_id"])
        set_parts = ["data = ?"]
        vals = [self._encode(doc)]
        if "$set" in update:
            for col in self._INDEX_COLS:
                if col in update["$set"]:
                    set_parts.append(f"{col} = ?")
                    vals.append(update["$set"][col])
        vals.append(doc_id)
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(f'UPDATE [{self.name}] SET {", ".join(set_parts)} WHERE _id = ?', vals)
            await conn.commit()

    def find(self, query: Dict) -> _SQLiteAsyncFind:
        return _SQLiteAsyncFind(self, query)

    async def _find_all(self, query: Dict) -> List[Dict]:
        await self._auto_ensure()
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as conn:
            try:
                sf = {k:v for k,v in query.items() if k in self._INDEX_COLS and not isinstance(v, dict)}
                cf = {k:v for k,v in query.items() if k not in sf}
                if sf:
                    where = " AND ".join(f"{k} = ?" for k in sf)
                    cur = await conn.execute(f'SELECT data FROM [{self.name}] WHERE {where}', list(sf.values()))
                else:
                    cur = await conn.execute(f'SELECT data FROM [{self.name}]')
                rows = await cur.fetchall()
            except Exception: return []
        results = []
        for (blob,) in rows:
            doc = self._decode(blob)
            if not cf or self._match(doc, cf): results.append(doc)
        return results

    async def create_index(self, *args, **kwargs): pass


# ═══════════════════════════════════════════════════════════════════════════
#  MongoDB Implementation
# ═══════════════════════════════════════════════════════════════════════════

class _MongoAsyncCursor(_AsyncCursor):
    def __init__(self, cursor):
        self._cursor = cursor

    def sort(self, key: str, direction: int = 1):
        self._cursor.sort(key, direction)
        return self

    async def to_list(self, length: int = 100) -> List[Dict]:
        cursor_list = await self._cursor.to_list(length=length)
        return cursor_list


class MongoCollection:
    def __init__(self, motor_collection):
        self._collection = motor_collection

    async def find_one(self, query: Dict) -> Optional[Dict]:
        # MongoDB uses _id as ObjectId by default if not string. 
        # But we use string IDs.
        return await self._collection.find_one(query)

    async def insert_one(self, doc: Dict) -> _InsertOneResult:
        if "_id" not in doc:
            doc["_id"] = uuid.uuid4().hex[:24]
        result = await self._collection.insert_one(doc)
        return _InsertOneResult(result.inserted_id)

    async def update_one(self, query: Dict, update: Dict):
        await self._collection.update_one(query, update)

    def find(self, query: Dict) -> _AsyncCursor:
        return _MongoAsyncCursor(self._collection.find(query))

    async def create_index(self, *args, **kwargs):
        await self._collection.create_index(*args, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════
#  Lifecycle
# ═══════════════════════════════════════════════════════════════════════════

client = None

async def init_database():
    """Initialise the database backend."""
    global users_collection, sessions_collection, client

    if settings.use_mongodb and settings.mongodb_uri:
        from motor.motor_asyncio import AsyncIOMotorClient
        import certifi
        uri = settings.mongodb_uri
        if "<db_password>" in uri:
            logger.warning("  DATABASE: MONGODB_URI still contains <db_password> placeholder. "
                           "Using SQLite fail safe as requested by the client.")
            # We purposely skip MongoDB connection and simulate a fallback
            client = None
            settings.use_mongodb = False
            await init_database()
            return

        logger.info("  DATABASE: Attempting MongoDB...")

        try:
            client = AsyncIOMotorClient(
                uri,
                serverSelectionTimeoutMS=5000,
                tlsCAFile=certifi.where(),
            )
            # Ping to verify connection
            await client.admin.command('ping')
            
            db = client.get_database("ai_interview")
            users_collection = MongoCollection(db.get_collection("users"))
            sessions_collection = MongoCollection(db.get_collection("sessions"))
            
            # Create indexes
            await users_collection.create_index("email", unique=True)
            await users_collection.create_index("username", unique=True)
            await sessions_collection.create_index("user_id")
            
            logger.info("  DATABASE: MongoDB Connected successfully.")
        except Exception as e:
            logger.warning(f"  DATABASE: MongoDB unavailable ({type(e).__name__}), using SQLite fallback.")
            settings.use_mongodb = False
            client = None
            await init_database()
            return
    else:
        logger.info("  DATABASE: Initializing SQLite (Failsafe SQL Mode)")
        users_collection = SQLiteCollection("users")
        sessions_collection = SQLiteCollection("sessions")
        # Ensure tables and indexes are ready
        await users_collection._ensure_table()
        await sessions_collection._ensure_table()
        logger.info("  DATABASE: SQLite ready at interview.sqlite")


async def close_database():
    global client
    if client:
        client.close()


def session_serializer(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc
