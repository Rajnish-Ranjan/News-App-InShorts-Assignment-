import os
import psycopg
from psycopg_pool import AsyncConnectionPool, ConnectionPool
from psycopg.rows import dict_row


class DBConnection:
    _instance = None
    _pool = None
    _conn_str = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DBConnection, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def connect(self, conn_str: str, min_size: int = 2, max_size: int = 10):
        if self._pool is not None:
            try:
                self._pool.close()
            except Exception:
                pass
        self._conn_str = conn_str
        self._pool = ConnectionPool(
            conninfo=conn_str,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row}
        )
        return self._pool

    def _ensure_pool(self):
        if self._pool is None:
            if self._conn_str:
                self.connect(self._conn_str)
            else:
                raise psycopg.OperationalError("Database pool is not initialized.")

    def execute(self, query: str, params: tuple = None):
        self._ensure_pool()
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()

    def execute_dml(self, query: str, params: tuple = None) -> int:
        self._ensure_pool()
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rowcount = cur.rowcount
                conn.commit()
                return rowcount

    def query(self, query: str, params: tuple = None) -> list:
        self._ensure_pool()
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()

    def close(self):
        if self._pool is not None:
            self._pool.close()
            self._pool = None


class AsyncDBConnection:
    _instance = None
    _pool = None
    _conn_str = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AsyncDBConnection, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    async def connect(self, conn_str: str, min_size: int = 2, max_size: int = 10):
        """
        Initialize the database connection pool.
        """
        if self._pool is not None:
            try:
                await self._pool.close()
            except Exception:
                pass
        self._conn_str = conn_str
        # Create it closed, then open it in the event loop explicitly
        self._pool = AsyncConnectionPool(
            conninfo=conn_str,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
            open=False
        )
        await self._pool.open()
        return self._pool

    async def _ensure_pool(self):
        if self._pool is None:
            if self._conn_str:
                await self.connect(self._conn_str)
            else:
                raise psycopg.OperationalError(
                    "Database pool is not initialized."
                )

    async def execute(self, query: str, params: tuple = None):
        await self._ensure_pool()
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                await conn.commit()

    async def execute_dml(self, query: str, params: tuple = None) -> int:
        await self._ensure_pool()
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                rowcount = cur.rowcount
                await conn.commit()
                return rowcount

    async def query(self, query: str, params: tuple = None) -> list:
        """
        Returns the results as a list of dictionaries.
        """
        await self._ensure_pool()
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                return await cur.fetchall()

    async def close(self):
        if self._pool is not None:
            await self._pool.close()
            self._pool = None


if __name__ == "__main__":
    import asyncio
    db = DBConnection()
    from utils import set_env

    set_env.set_cred_environments()
    async def main():
        await db.connect(os.getenv("NeonDB_URL"))
        print(await db.query("SELECT * FROM news_articles LIMIT 5"))
        await db.close()

    asyncio.run(main())
