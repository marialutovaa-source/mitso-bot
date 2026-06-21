from db.models import get_pool


async def get_user(tg_id: int):
    pool = await get_pool()
    return await pool.fetchrow("SELECT * FROM users WHERE tg_id = $1", tg_id)


async def create_user(tg_id: int, role: str = "student"):
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO users(tg_id, role) VALUES($1, $2) ON CONFLICT DO NOTHING",
        tg_id, role
    )


async def set_user_role(tg_id: int, role: str):
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO users(tg_id, role) VALUES($1, $2) "
        "ON CONFLICT(tg_id) DO UPDATE SET role = $2",
        tg_id, role
    )


async def get_all_admins():
    pool = await get_pool()
    return await pool.fetch("SELECT tg_id FROM users WHERE role IN ('admin', 'superadmin')")


async def add_student(last_name: str, first_name: str) -> int:
    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO students(last_name, first_name) VALUES($1, $2) "
        "ON CONFLICT DO NOTHING RETURNING id",
        last_name.strip(), first_name.strip()
