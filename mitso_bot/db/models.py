import asyncpg
from config import DATABASE_URL

_pool: asyncpg.Pool = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id           SERIAL PRIMARY KEY,
                last_name    TEXT NOT NULL,
                first_name   TEXT NOT NULL,
                created_at   TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(last_name, first_name)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id        BIGINT PRIMARY KEY,
                role         TEXT NOT NULL DEFAULT 'student',
                student_id   INTEGER REFERENCES students(id) ON DELETE SET NULL,
                created_at   TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        await conn.execute("""
            ALTER TABLE students
            ADD COLUMN IF NOT EXISTS tg_id BIGINT UNIQUE REFERENCES users(tg_id) ON DELETE SET NULL
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS disciplines (
                id    SERIAL PRIMARY KEY,
                name  TEXT NOT NULL UNIQUE
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS absences (
                id             SERIAL PRIMARY KEY,
                student_id     INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                discipline_id  INTEGER NOT NULL REFERENCES disciplines(id) ON DELETE CASCADE,
                date           DATE NOT NULL,
                hours          INTEGER NOT NULL DEFAULT 2,
                reason         TEXT,
                confirmed      BOOLEAN DEFAULT FALSE,
                created_at     TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS proof_photos (
                id          SERIAL PRIMARY KEY,
                student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                file_id     TEXT NOT NULL,
                caption     TEXT,
                sent_at     TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS absences_student_idx    ON absences(student_id);
            CREATE INDEX IF NOT EXISTS absences_discipline_idx ON absences(discipline_id);
            CREATE INDEX IF NOT EXISTS absences_date_idx       ON absences(date);
        """)
