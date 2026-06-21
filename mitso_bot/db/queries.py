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
    )
    if row:
        return row["id"]
    existing = await pool.fetchrow(
        "SELECT id FROM students WHERE last_name=$1 AND first_name=$2",
        last_name.strip(), first_name.strip()
    )
    return existing["id"] if existing else None


async def remove_student(student_id: int):
    pool = await get_pool()
    await pool.execute("DELETE FROM students WHERE id = $1", student_id)


async def get_all_students():
    pool = await get_pool()
    return await pool.fetch(
        "SELECT s.*, u.tg_id FROM students s "
        "LEFT JOIN users u ON u.student_id = s.id "
        "ORDER BY s.last_name, s.first_name"
    )


async def get_student_by_name(last_name: str, first_name: str):
    pool = await get_pool()
    return await pool.fetchrow(
        "SELECT * FROM students WHERE lower(last_name)=lower($1) AND lower(first_name)=lower($2)",
        last_name.strip(), first_name.strip()
    )


async def link_student_to_user(tg_id: int, student_id: int):
    pool = await get_pool()
    await pool.execute(
        "UPDATE students SET tg_id = $1 WHERE id = $2", tg_id, student_id
    )
    await pool.execute(
        "UPDATE users SET student_id = $1 WHERE tg_id = $2", student_id, tg_id
    )


async def get_or_create_discipline(name: str) -> int:
    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO disciplines(name) VALUES($1) ON CONFLICT(name) DO UPDATE SET name=EXCLUDED.name RETURNING id",
        name.strip()
    )
    return row["id"]


async def get_all_disciplines():
    pool = await get_pool()
    return await pool.fetch("SELECT * FROM disciplines ORDER BY name")


async def add_absence(student_id: int, discipline_id: int, date,
                      hours: int = 2, reason: str = None,
                      lesson_num: int = None, lesson_time: str = None):
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO absences(student_id, discipline_id, date, hours, reason, lesson_num, lesson_time) "
        "VALUES($1,$2,$3,$4,$5,$6,$7)",
        student_id, discipline_id, date, hours, reason, lesson_num, lesson_time
    )


async def delete_absence(absence_id: int):
    pool = await get_pool()
    await pool.execute("DELETE FROM absences WHERE id = $1", absence_id)


async def confirm_absence(absence_id: int):
    pool = await get_pool()
    await pool.execute("UPDATE absences SET confirmed=TRUE WHERE id = $1", absence_id)


async def get_absences(student_id: int = None, discipline_id: int = None,
                       date_from=None, date_to=None):
    pool = await get_pool()
    conditions = []
    args = []
    i = 1
    if student_id:
        conditions.append(f"a.student_id = ${i}"); args.append(student_id); i += 1
    if discipline_id:
        conditions.append(f"a.discipline_id = ${i}"); args.append(discipline_id); i += 1
    if date_from:
        conditions.append(f"a.date >= ${i}"); args.append(date_from); i += 1
    if date_to:
        conditions.append(f"a.date <= ${i}"); args.append(date_to); i += 1
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return await pool.fetch(f"""
        SELECT a.*, s.last_name, s.first_name, d.name AS discipline
        FROM absences a
        JOIN students s ON s.id = a.student_id
        JOIN disciplines d ON d.id = a.discipline_id
        {where}
        ORDER BY a.date DESC, s.last_name
    """, *args)


async def get_student_total_hours(student_id: int) -> int:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT COALESCE(SUM(hours), 0) AS total FROM absences WHERE student_id = $1",
        student_id
    )
    return row["total"]


async def save_proof_photo(student_id: int, file_id: str, caption: str = None):
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO proof_photos(student_id, file_id, caption) VALUES($1,$2,$3)",
        student_id, file_id, caption
    )


async def get_student_photos(student_id: int):
    pool = await get_pool()
    return await pool.fetch(
        "SELECT * FROM proof_photos WHERE student_id = $1 ORDER BY sent_at DESC",
        student_id
    )    )
    if row:
        return row["id"]
    existing = await pool.fetchrow(
        "SELECT id FROM students WHERE last_name=$1 AND first_name=$2",
        last_name.strip(), first_name.strip()
    )
    return existing["id"] if existing else None


async def remove_student(student_id: int):
    pool = await get_pool()
    await pool.execute("DELETE FROM students WHERE id = $1", student_id)


async def get_all_students():
    pool = await get_pool()
    return await pool.fetch(
        "SELECT s.*, u.tg_id FROM students s "
        "LEFT JOIN users u ON u.student_id = s.id "
        "ORDER BY s.last_name, s.first_name"
    )


async def get_student_by_name(last_name: str, first_name: str):
    pool = await get_pool()
    return await pool.fetchrow(
        "SELECT * FROM students WHERE lower(last_name)=lower($1) AND lower(first_name)=lower($2)",
        last_name.strip(), first_name.strip()
    )


async def link_student_to_user(tg_id: int, student_id: int):
    pool = await get_pool()
    await pool.execute(
        "UPDATE students SET tg_id = $1 WHERE id = $2", tg_id, student_id
    )
    await pool.execute(
        "UPDATE users SET student_id = $1 WHERE tg_id = $2", student_id, tg_id
    )


async def get_or_create_discipline(name: str) -> int:
    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO disciplines(name) VALUES($1) ON CONFLICT(name) DO UPDATE SET name=EXCLUDED.name RETURNING id",
        name.strip()
    )
    return row["id"]


async def get_all_disciplines():
    pool = await get_pool()
    return await pool.fetch("SELECT * FROM disciplines ORDER BY name")


async def add_absence(student_id: int, discipline_id: int, date, hours: int = 2, reason: str = None):
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO absences(student_id, discipline_id, date, hours, reason) VALUES($1,$2,$3,$4,$5)",
        student_id, discipline_id, date, hours, reason
    )


async def delete_absence(absence_id: int):
    pool = await get_pool()
    await pool.execute("DELETE FROM absences WHERE id = $1", absence_id)


async def confirm_absence(absence_id: int):
    pool = await get_pool()
    await pool.execute("UPDATE absences SET confirmed=TRUE WHERE id = $1", absence_id)


async def get_absences(student_id: int = None, discipline_id: int = None,
                       date_from=None, date_to=None):
    pool = await get_pool()
    conditions = []
    args = []
    i = 1
    if student_id:
        conditions.append(f"a.student_id = ${i}"); args.append(student_id); i += 1
    if discipline_id:
        conditions.append(f"a.discipline_id = ${i}"); args.append(discipline_id); i += 1
    if date_from:
        conditions.append(f"a.date >= ${i}"); args.append(date_from); i += 1
    if date_to:
        conditions.append(f"a.date <= ${i}"); args.append(date_to); i += 1
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return await pool.fetch(f"""
        SELECT a.*, s.last_name, s.first_name, d.name AS discipline
        FROM absences a
        JOIN students s ON s.id = a.student_id
        JOIN disciplines d ON d.id = a.discipline_id
        {where}
        ORDER BY a.date DESC, s.last_name
    """, *args)


async def get_student_total_hours(student_id: int) -> int:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT COALESCE(SUM(hours), 0) AS total FROM absences WHERE student_id = $1",
        student_id
    )
    return row["total"]


async def save_proof_photo(student_id: int, file_id: str, caption: str = None):
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO proof_photos(student_id, file_id, caption) VALUES($1,$2,$3)",
        student_id, file_id, caption
    )


async def get_student_photos(student_id: int):
    pool = await get_pool()
    return await pool.fetch(
        "SELECT * FROM proof_photos WHERE student_id = $1 ORDER BY sent_at DESC",
        student_id
    )
