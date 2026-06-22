import os
import psycopg
from psycopg_pool import ConnectionPool
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
        """
        Initialize the database connection pool.
        """
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
                raise psycopg.OperationalError(
                    "Database pool is not initialized."
                )

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
        """
        Returns the results as a list of dictionaries.
        """
        self._ensure_pool()
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()

    def close(self):
        if self._pool is not None:
            self._pool.close()
            self._pool = None


if __name__ == "__main__":
    db = DBConnection()
    from utils import set_env

    set_env.set_cred_environments()
    db.connect(os.getenv("NeonDB_URL"))
    print(db.query("SELECT * FROM news_articles LIMIT 5"))
    db.close()
