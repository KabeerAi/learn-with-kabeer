import os
import sqlite3
from datetime import datetime, timedelta

from flask import current_app, g
import psycopg2
import psycopg2.extras

class DuplicateEmailError(Exception):
    pass


# ─── Cross-Database Compatibility Wrappers ────────────────────────────────────

class PostgresRow:
    """Mimics sqlite3.Row behavior for seamless dictionary conversion and indexing."""
    def __init__(self, keys, values):
        self._keys = keys
        self._values = values
        self._mapping = dict(zip(keys, values))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._mapping[key]

    def keys(self):
        return self._keys

    def items(self):
        return self._mapping.items()

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        return iter(self._values)

    def __repr__(self):
        return repr(self._mapping)


class PostgresCursorWrapper:
    """Adapts Postgres cursor execution behaviors to match SQLite patterns."""
    def __init__(self, cursor):
        self.cursor = cursor
        self._lastrowid = None

    @property
    def lastrowid(self):
        """Exposes lastrowid to match SQLite's connection property."""
        return self._lastrowid

    def execute(self, query, params=None):
        # 1. Handle placeholder swap (? to %s)
        query = query.replace('?', '%s')
        
        # 2. Transpile SQLite scalar min/max to Postgres least/greatest
        if "MAX(completed_lessons," in query:
            query = query.replace("MAX(completed_lessons,", "GREATEST(completed_lessons,")
        if "MIN(completed_lessons," in query:
            query = query.replace("MIN(completed_lessons,", "LEAST(completed_lessons,")
            
        # 3. Transpile SQLite INSERT OR IGNORE patterns
        if "INSERT OR IGNORE INTO career_path_enrollments" in query:
            query = "INSERT INTO career_path_enrollments (user_id, career_path_id) VALUES (%s, %s) ON CONFLICT DO NOTHING"
        elif "INSERT OR IGNORE INTO career_path_courses" in query:
            query = "INSERT INTO career_path_courses (career_path_id, course_id, number) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING"

        # 4. Handle auto-incrementing ID tracking safely
        is_insert = query.strip().upper().startswith("INSERT")
        if is_insert and "RETURNING" not in query.upper() and "ON CONFLICT DO NOTHING" not in query.upper():
            # Use RETURNING * and extract 'id' if it exists to avoid UndefinedColumn errors
            # on tables like system_jobs which use a custom primary key
            query += " RETURNING *"
            self.cursor.execute(query, params or ())
            try:
                row = self.cursor.fetchone()
                if row and self.cursor.description:
                    colnames = [d[0].lower() for d in self.cursor.description]
                    if 'id' in colnames:
                        self._lastrowid = row[colnames.index('id')]
            except Exception:
                pass
        else:
            self.cursor.execute(query, params or ())
        return self

    def _wrap_row(self, row):
        if row is None:
            return None
        if self.cursor.description:
            keys = [desc[0] for desc in self.cursor.description]
            return PostgresRow(keys, row)
        return row

    def fetchone(self):
        try:
            row = self.cursor.fetchone()
            return self._wrap_row(row)
        except (psycopg2.ProgrammingError, psycopg2.OperationalError):
            return None

    def fetchall(self):
        try:
            rows = self.cursor.fetchall()
            return [self._wrap_row(r) for r in rows]
        except (psycopg2.ProgrammingError, psycopg2.OperationalError):
            return []

    def __iter__(self):
        try:
            for row in self.cursor:
                yield self._wrap_row(row)
        except (psycopg2.ProgrammingError, psycopg2.OperationalError):
            return

    def __getattr__(self, name):
        return getattr(self.cursor, name)


class PostgresConnWrapper:
    """Adapts Postgres connection execution shortcuts to match SQLite behavior."""
    def __init__(self, conn):
        self.conn = conn

    def execute(self, query, params=None):
        cursor = self.conn.cursor()
        wrapper = PostgresCursorWrapper(cursor)
        wrapper.execute(query, params)
        return wrapper

    def executescript(self, script):
        # Convert table creation syntax to Postgres standards
        script = script.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        cursor = self.conn.cursor()
        cursor.execute(script)
        return cursor

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    def __getattr__(self, name):
        return getattr(self.conn, name)


# ─── App Setup and Lifetime Hooks ───────────────────────────────────────────

def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()


def get_db():
    if "db" not in g:
        db_uri = current_app.config["DATABASE"]
        if db_uri.startswith(("postgresql://", "postgres://")):
            conn = psycopg2.connect(db_uri)
            g.db = PostgresConnWrapper(conn)
        else:
            g.db = sqlite3.connect(db_uri)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    is_postgres = current_app.config["DATABASE"].startswith("postgresql://")
    
    if not is_postgres:
        os.makedirs(current_app.instance_path, exist_ok=True)
        db = sqlite3.connect(current_app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    else:
        # Get your postgres connection from your wrapper setup
        db = g.pop("db", None) or get_db()

    # The raw string containing your tables
    schema_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            is_pro INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            total_xp INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            course_id INTEGER,
            activity_type TEXT NOT NULL,
            xp_amount INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS courses (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            slug TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            subtitle TEXT NOT NULL,
            level TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS sections (
            id SERIAL PRIMARY KEY,
            course_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            number INTEGER NOT NULL,
            background TEXT,
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
            UNIQUE (course_id, number)
        );

        CREATE TABLE IF NOT EXISTS lessons (
            id SERIAL PRIMARY KEY,
            course_id INTEGER NOT NULL,
            section_id INTEGER,
            number INTEGER NOT NULL,
            slug TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            route_name TEXT,
            content TEXT,
            builder_json TEXT,
            plan_json TEXT,
            content_type TEXT NOT NULL DEFAULT 'html',
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
            FOREIGN KEY (section_id) REFERENCES sections (id) ON DELETE SET NULL,
            UNIQUE (course_id, number)
        );

        CREATE TABLE IF NOT EXISTS progress (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            current_lesson_id INTEGER NOT NULL,
            completed_lessons INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
            UNIQUE (user_id, course_id)
        );

        CREATE TABLE IF NOT EXISTS career_paths (
            id SERIAL PRIMARY KEY,
            slug TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            subtitle TEXT NOT NULL,
            description TEXT,
            level TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS career_path_courses (
            career_path_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            number INTEGER NOT NULL,
            PRIMARY KEY (career_path_id, course_id),
            FOREIGN KEY (career_path_id) REFERENCES career_paths (id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
            UNIQUE (career_path_id, number)
        );

        CREATE TABLE IF NOT EXISTS career_path_enrollments (
            user_id INTEGER NOT NULL,
            career_path_id INTEGER NOT NULL,
            enrolled_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, career_path_id),
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (career_path_id) REFERENCES career_paths (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS system_jobs (
            job_id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending',
            progress_percent INTEGER NOT NULL DEFAULT 0,
            current_title TEXT,
            result_url TEXT,
            error_message TEXT,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        -- AI Vector Store (for Render/Postgres)
        DO $$ 
        BEGIN 
            IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector') THEN
                CREATE EXTENSION IF NOT EXISTS vector;
                CREATE TABLE IF NOT EXISTS educational_chunks (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector(768),
                    metadata JSONB,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            END IF;
        END $$;
    """

    # SAFE EXECUTION TRICK FOR BOTH DRIVERS:
    if is_postgres:
        # SQLite uses AUTOINCREMENT, Postgres uses SERIAL (handled above)
        # Split statements by semicolon and run them one by one
        for statement in schema_sql.split(";"):
            clean_statement = statement.strip()
            if clean_statement:
                db.execute(clean_statement)
        db.commit()
    else:
        # Fallback for local SQLite machine
        sqlite_schema = schema_sql.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
        sqlite_schema = sqlite_schema.replace("TIMESTAMP", "TEXT")
        db.executescript(sqlite_schema)
        db.commit()

    # Migration tracking context catches errors gracefully and handles aborted transactions for Postgres
    try:
        db.execute("ALTER TABLE lessons ADD COLUMN content_type TEXT NOT NULL DEFAULT 'html'")
        db.commit()
    except (sqlite3.OperationalError, psycopg2.Error):
        if is_postgres: db.rollback()

    try:
        db.execute("ALTER TABLE lessons ADD COLUMN section_id INTEGER REFERENCES sections(id) ON DELETE SET NULL")
        db.commit()
    except (sqlite3.OperationalError, psycopg2.Error):
        if is_postgres: db.rollback()

    try:
        db.execute("ALTER TABLE sections ADD COLUMN background TEXT")
        db.commit()
    except (sqlite3.OperationalError, psycopg2.Error):
        if is_postgres: db.rollback()

    try:
        db.execute("ALTER TABLE lessons ADD COLUMN builder_json TEXT")
        db.commit()
    except (sqlite3.OperationalError, psycopg2.Error):
        if is_postgres: db.rollback()

    try:
        db.execute("ALTER TABLE lessons ADD COLUMN plan_json TEXT")
        db.commit()
    except (sqlite3.OperationalError, psycopg2.Error):
        if is_postgres: db.rollback()

    try:
        db.execute("ALTER TABLE users ADD COLUMN total_xp INTEGER NOT NULL DEFAULT 0")
        db.commit()
    except (sqlite3.OperationalError, psycopg2.Error):
        if is_postgres: db.rollback()

    try:
        db.execute("ALTER TABLE users ADD COLUMN is_pro INTEGER NOT NULL DEFAULT 0")
        db.commit()
    except (sqlite3.OperationalError, psycopg2.Error):
        if is_postgres: db.rollback()

    try:
        db.execute("ALTER TABLE courses ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE")
        db.commit()
    except (sqlite3.OperationalError, psycopg2.Error):
        if is_postgres: db.rollback()

    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS system_jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'pending',
                progress_percent INTEGER NOT NULL DEFAULT 0,
                current_title TEXT,
                result_url TEXT,
                error_message TEXT,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
    except (sqlite3.OperationalError, psycopg2.Error):
        if is_postgres: db.rollback()

    # 1. Safely check if the 'users' table exists before trying to query it
    if is_postgres:
        table_check = db.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"
        ).fetchone()
        # Handle dict or tuple format safely
        table_exists = table_check["exists"] if isinstance(table_check, dict) or hasattr(table_check, 'keys') else table_check[0]
    else:
        # For local SQLite setup
        table_check = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        table_exists = table_check is not None

    # 2. Only run seeding if the table exists
    if table_exists:
        user_count_row = db.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()
        # Extract the count based on row structure
        if isinstance(user_count_row, dict) or hasattr(user_count_row, 'keys'):
            user_count = user_count_row["cnt"]
        else:
            user_count = user_count_row[0]

        if user_count == 0:
            from werkzeug.security import generate_password_hash
            admin_pass = generate_password_hash("admin123")
            
            # Use %s placeholder for Postgres, and ? for SQLite
            placeholder = "%s" if is_postgres else "?"
            
            db.execute(
                f"INSERT INTO users (name, email, password_hash, is_admin, total_xp) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})",
                ("Administrator", "admin@learnwithkabeer.com", admin_pass, 1, 100000)
            )
            db.commit()

        # Safely enforce the admin XP minimum
        db.execute("UPDATE users SET total_xp = 100000 WHERE is_admin = 1 AND total_xp < 100000")
        db.commit()

    db.close()



# ─── User Queries ───────────────────────────────────────────────────────────

def get_user_by_id(user_id):
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_user_by_email(email):
    return get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def create_user(name, email, password_hash):
    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        db.commit()
    except (sqlite3.IntegrityError, psycopg2.IntegrityError) as exc:
        raise DuplicateEmailError from exc
    return get_user_by_email(email)


# ─── Progress Queries ───────────────────────────────────────────────────────

def get_progress(user_id, course_id):
    return get_db().execute(
        "SELECT * FROM progress WHERE user_id = ? AND course_id = ?",
        (user_id, course_id),
    ).fetchone()


def ensure_progress(user_id, course_id, first_lesson_id):
    db = get_db()
    progress = get_progress(user_id, course_id)
    if progress:
        return progress

    db.execute(
        "INSERT INTO progress (user_id, course_id, current_lesson_id) VALUES (?, ?, ?)",
        (user_id, course_id, first_lesson_id),
    )
    db.commit()
    return get_progress(user_id, course_id)


def enroll_user_in_course(user_id, course_slug):
    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE slug = ?", (course_slug,)).fetchone()
    if course is None or course["status"] != "active":
        return None

    first_lesson = db.execute(
        "SELECT * FROM lessons WHERE course_id = ? ORDER BY number LIMIT 1",
        (course["id"],),
    ).fetchone()
    if first_lesson is None:
        return None

    return ensure_progress(user_id, course["id"], first_lesson["id"])


def enroll_user_in_career_path(user_id, path_slug):
    db = get_db()
    path = db.execute("SELECT * FROM career_paths WHERE slug = ?", (path_slug,)).fetchone()
    if path is None or path["status"] != "active":
        return False

    db.execute(
        "INSERT OR IGNORE INTO career_path_enrollments (user_id, career_path_id) VALUES (?, ?)",
        (user_id, path["id"])
    )
    db.commit()
    return True


# ─── Course Queries ─────────────────────────────────────────────────────────

def get_course_by_id(course_id):
    return get_db().execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()


def get_course_library(user=None, include_private=True):
    db = get_db()
    
    query = """
        SELECT c.*,
               (SELECT COUNT(*) FROM lessons WHERE course_id = c.id) AS total_lessons,
               (SELECT COUNT(*) FROM progress WHERE course_id = c.id) AS enrolled_count
        FROM courses c
    """
    params = []
    
    if user:
        if user["is_admin"]:
            if not include_private:
                query += " WHERE c.user_id IS NULL"
        else:
            if include_private:
                query += " WHERE c.user_id IS NULL OR c.user_id = ?"
                params.append(user["id"])
            else:
                query += " WHERE c.user_id IS NULL"
    else:
        query += " WHERE c.user_id IS NULL"
        
    query += """
        ORDER BY
            CASE c.status WHEN 'active' THEN 0 ELSE 1 END,
            c.id
    """
    courses = db.execute(query, params).fetchall()

    library = []
    for course in courses:
        lessons = db.execute(
            "SELECT * FROM lessons WHERE course_id = ? ORDER BY number",
            (course["id"],),
        ).fetchall()

        sections_raw = db.execute(
            "SELECT * FROM sections WHERE course_id = ? ORDER BY number",
            (course["id"],),
        ).fetchall()

        grouped_sections = []
        for s in sections_raw:
            sec_lessons = [dict(l) for l in lessons if l["section_id"] == s["id"]]
            grouped_sections.append({
                "id": s["id"],
                "title": s["title"],
                "description": s["description"],
                "number": s["number"],
                "background": s["background"],
                "lessons": sec_lessons
            })

        misc_lessons = [dict(l) for l in lessons if l["section_id"] is None]
        if misc_lessons:
            grouped_sections.append({
                "id": None,
                "title": "Unassigned Lessons",
                "description": "Lessons not assigned to any section",
                "number": 999,
                "lessons": misc_lessons
            })

        if not grouped_sections:
            grouped_sections.append({
                "id": None,
                "title": "Course Curriculum",
                "description": "",
                "number": 1,
                "lessons": [dict(l) for l in lessons]
            })
        progress = get_progress(user["id"], course["id"]) if user else None
        current_lesson = lessons[0] if lessons else None

        if progress and progress["current_lesson_id"]:
            found = db.execute(
                "SELECT * FROM lessons WHERE id = ?",
                (progress["current_lesson_id"],),
            ).fetchone()
            if found:
                current_lesson = found

        completed_lessons = progress["completed_lessons"] if progress else 0
        total = course["total_lessons"]
        progress_percent = round((completed_lessons / total) * 100) if total else 0

        item = dict(course)
        item.update({
            "lessons": [dict(l) for l in lessons],
            "sections": grouped_sections,
            "current_lesson": dict(current_lesson) if current_lesson else None,
            "completed_lessons": completed_lessons,
            "enrolled": progress is not None,
            "progress": dict(progress) if progress else None,
            "progress_percent": progress_percent,
            "total_lessons": total,
        })
        library.append(item)

    return library


def get_admin_stats():
    db = get_db()
    total_users = db.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()["cnt"]
    total_completions = db.execute("SELECT SUM(completed_lessons) AS cnt FROM progress").fetchone()["cnt"] or 0
    total_lessons = db.execute("SELECT COUNT(*) AS cnt FROM lessons").fetchone()["cnt"]
    total_enrollments = db.execute("SELECT COUNT(*) AS cnt FROM progress").fetchone()["cnt"]
    
    popular_courses = db.execute("""
        SELECT c.title, COUNT(p.id) as enrollments
        FROM courses c
        LEFT JOIN progress p ON c.id = p.course_id
        GROUP BY c.id, c.title
        ORDER BY enrollments DESC
        LIMIT 3
    """).fetchall()

    return {
        "total_users": total_users,
        "total_completions": total_completions,
        "total_lessons": total_lessons,
        "total_enrollments": total_enrollments,
        "popular_courses": [dict(c) for c in popular_courses]
    }


def get_course_overview(user=None, course_slug=None):
    db = get_db()
    
    if not course_slug and user:
        latest = db.execute("""
            SELECT c.slug 
            FROM progress p 
            JOIN courses c ON p.course_id = c.id 
            WHERE p.user_id = ? 
            ORDER BY p.updated_at DESC 
            LIMIT 1
        """, (user["id"],)).fetchone()
        if latest:
            course_slug = latest["slug"]

    if not course_slug:
        first = db.execute("SELECT slug FROM courses WHERE status = 'active' ORDER BY id LIMIT 1").fetchone()
        course_slug = first["slug"] if first else "python"

    course = db.execute("SELECT * FROM courses WHERE slug = ?", (course_slug,)).fetchone()
    if course is None:
        return {
            "course": None, "lessons": [], "sections": [], "progress": None, "enrolled": False,
            "courses": [], "enrolled_courses": [], "current_lesson": None,
            "completed_lessons": 0, "progress_percent": 0, "total_lessons": 0,
        }

    if course["user_id"] is not None:
        if not user or (not user["is_admin"] and user["id"] != course["user_id"]):
            return {
                "course": None, "lessons": [], "sections": [], "progress": None, "enrolled": False,
                "courses": [], "enrolled_courses": [], "current_lesson": None,
                "completed_lessons": 0, "progress_percent": 0, "total_lessons": 0,
            }

    lessons = db.execute(
        "SELECT * FROM lessons WHERE course_id = ? ORDER BY number",
        (course["id"],),
    ).fetchall()

    sections_raw = db.execute(
        "SELECT * FROM sections WHERE course_id = ? ORDER BY number",
        (course["id"],),
    ).fetchall()

    progress = None
    current_lesson = lessons[0] if lessons else None

    if user:
        progress = get_progress(user["id"], course["id"])
        if progress and progress["current_lesson_id"]:
            found = db.execute(
                "SELECT * FROM lessons WHERE id = ?",
                (progress["current_lesson_id"],),
            ).fetchone()
            if found:
                current_lesson = found

    completed_lessons = progress["completed_lessons"] if progress else 0
    total = len(lessons)
    progress_percent = round((completed_lessons / total) * 100) if total else 0
    courses = get_course_library(user)
    enrolled_courses = [c for c in courses if c["enrolled"]]

    sections = []
    
    misc_lessons = [dict(l) for l in lessons if l["section_id"] is None]
    if misc_lessons:
        sections.append({
            "id": None,
            "title": "Unit 1" if not sections_raw else "Getting Started",
            "description": "The fundamentals of this path",
            "number": 0,
            "lessons": misc_lessons
        })

    for s in sections_raw:
        sec_lessons = [dict(l) for l in lessons if l["section_id"] == s["id"]]
        sections.append({
            "id": s["id"],
            "title": s["title"],
            "description": s["description"],
            "number": s["number"],
            "background": s["background"],
            "lessons": sec_lessons
        })

    if not lessons and not sections_raw:
        sections = []

    course_dict = dict(course)
    course_dict.update({
        "total_lessons": total,
        "progress_percent": progress_percent,
        "completed_lessons": completed_lessons,
    })

    return {
        "course": course_dict,
        "lessons": [dict(l) for l in lessons],
        "sections": sections,
        "progress": dict(progress) if progress else None,
        "enrolled": progress is not None,
        "courses": courses,
        "enrolled_courses": enrolled_courses,
        "current_lesson": dict(current_lesson) if current_lesson else None,
        "completed_lessons": completed_lessons,
        "progress_percent": progress_percent,
        "total_lessons": total,
    }


def create_course(slug, title, subtitle, level, status, user_id=None):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO courses (slug, title, subtitle, level, status, user_id) VALUES (?, ?, ?, ?, ?, ?)",
        (slug, title, subtitle, level, status, user_id),
    )
    course_id = cursor.lastrowid
    db.commit()
    return db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()


def update_course(course_id, slug, title, subtitle, level, status):
    db = get_db()
    db.execute(
        "UPDATE courses SET slug = ?, title = ?, subtitle = ?, level = ?, status = ? WHERE id = ?",
        (slug, title, subtitle, level, status, course_id),
    )
    db.commit()


def delete_course(course_id):
    db = get_db()
    affected_paths = db.execute(
        "SELECT DISTINCT career_path_id FROM career_path_courses WHERE course_id = ?",
        (course_id,)
    ).fetchall()

    affected_users = db.execute(
        "SELECT COUNT(*) AS cnt FROM progress WHERE course_id = ?", (course_id,)
    ).fetchone()["cnt"]

    db.execute("DELETE FROM courses WHERE id = ?", (course_id,))

    for row in affected_paths:
        _reorder_all_courses_in_career_path(row["career_path_id"])

    db.commit()
    return affected_users


def _reorder_all_courses_in_career_path(path_id):
    db = get_db()
    courses = db.execute(
        "SELECT course_id FROM career_path_courses WHERE career_path_id = ? ORDER BY number",
        (path_id,)
    ).fetchall()
    
    for cid in courses:
        db.execute(
            "UPDATE career_path_courses SET number = number + 1000 WHERE career_path_id = ? AND course_id = ?",
            (path_id, cid["course_id"])
        )
        
    for idx, cid in enumerate(courses, start=1):
        db.execute(
            "UPDATE career_path_courses SET number = ? WHERE career_path_id = ? AND course_id = ?",
            (idx, path_id, cid["course_id"])
        )
    db.commit()


# ─── Career Path Queries ────────────────────────────────────────────────────

def get_career_paths(user_id=None):
    db = get_db()
    paths = db.execute("SELECT * FROM career_paths ORDER BY id DESC").fetchall()
    result = []
    for p in paths:
        path_dict = dict(p)
        count = db.execute(
            "SELECT COUNT(*) AS cnt FROM career_path_courses WHERE career_path_id = ?",
            (p["id"],)
        ).fetchone()["cnt"]
        path_dict["course_count"] = count

        if user_id:
            enrolled = db.execute("""
                SELECT 1 FROM career_path_enrollments 
                WHERE career_path_id = ? AND user_id = ?
                LIMIT 1
            """, (p["id"], user_id)).fetchone()
            path_dict["enrolled"] = enrolled is not None
        else:
            path_dict["enrolled"] = False

        result.append(path_dict)
    return result


def get_career_path_by_slug(slug, user=None):
    db = get_db()
    path = db.execute("SELECT * FROM career_paths WHERE slug = ?", (slug,)).fetchone()
    if not path:
        return None

    path_dict = dict(path)
    path_dict["enrolled"] = False
    if user:
        enrolled = db.execute(
            "SELECT 1 FROM career_path_enrollments WHERE career_path_id = ? AND user_id = ?",
            (path["id"], user["id"])
        ).fetchone()
        path_dict["enrolled"] = enrolled is not None

    courses = db.execute("""
        SELECT c.*, cpc.number 
        FROM courses c
        JOIN career_path_courses cpc ON c.id = cpc.course_id
        WHERE cpc.career_path_id = ?
        ORDER BY cpc.number
    """, (path["id"],)).fetchall()
    
    path_dict["courses"] = []
    for c in courses:
        c_dict = dict(c)
        if user:
            prog = db.execute(
                "SELECT 1 FROM progress WHERE course_id = ? AND user_id = ?",
                (c["id"], user["id"])
            ).fetchone()
            c_dict["enrolled"] = prog is not None
        else:
            c_dict["enrolled"] = False
        path_dict["courses"].append(c_dict)

    return path_dict


def get_career_path_by_id(path_id):
    return get_db().execute("SELECT * FROM career_paths WHERE id = ?", (path_id,)).fetchone()


def create_career_path(slug, title, subtitle, description, level, status):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO career_paths (slug, title, subtitle, description, level, status) VALUES (?, ?, ?, ?, ?, ?)",
        (slug, title, subtitle, description, level, status),
    )
    path_id = cursor.lastrowid
    db.commit()
    return path_id


def update_career_path(path_id, slug, title, subtitle, description, level, status):
    db = get_db()
    db.execute(
        "UPDATE career_paths SET slug = ?, title = ?, subtitle = ?, description = ?, level = ?, status = ? WHERE id = ?",
        (slug, title, subtitle, description, level, status, path_id),
    )
    db.commit()


def delete_career_path(path_id):
    db = get_db()
    db.execute("DELETE FROM career_paths WHERE id = ?", (path_id,))
    db.commit()


def add_course_to_career_path(path_id, course_id, number=None):
    db = get_db()
    if number is None:
        res = db.execute(
            "SELECT MAX(number) AS max_n FROM career_path_courses WHERE career_path_id = ?",
            (path_id,)
        ).fetchone()
        number = (res["max_n"] or 0) + 1

    db.execute(
        "INSERT OR IGNORE INTO career_path_courses (career_path_id, course_id, number) VALUES (?, ?, ?)",
        (path_id, course_id, number)
    )
    db.commit()


def remove_course_from_career_path(path_id, course_id):
    db = get_db()
    db.execute(
        "DELETE FROM career_path_courses WHERE career_path_id = ? AND course_id = ?",
        (path_id, course_id)
    )
    db.commit()


def reorder_career_path_courses(path_id, course_ids):
    db = get_db()
    for cid in course_ids:
        db.execute(
            "UPDATE career_path_courses SET number = number + 1000 WHERE career_path_id = ? AND course_id = ?",
            (path_id, cid)
        )
    for idx, cid in enumerate(course_ids, start=1):
        db.execute(
            "UPDATE career_path_courses SET number = ? WHERE career_path_id = ? AND course_id = ?",
            (idx, path_id, cid)
        )
    db.commit()


# ─── Section Queries ────────────────────────────────────────────────────────

def get_sections_by_course(course_id):
    return get_db().execute(
        "SELECT * FROM sections WHERE course_id = ? ORDER BY number", (course_id,)
    ).fetchall()


def get_section_by_id(section_id):
    return get_db().execute("SELECT * FROM sections WHERE id = ?", (section_id,)).fetchone()


def create_section(course_id, number, title, description, background=None):
    db = get_db()
    db.execute(
        "INSERT INTO sections (course_id, number, title, description, background) VALUES (?, ?, ?, ?, ?)",
        (course_id, number, title, description, background),
    )
    db.commit()
    return db.execute(
        "SELECT * FROM sections WHERE course_id = ? AND number = ?", (course_id, number)
    ).fetchone()


def update_section(section_id, number, title, description, background=None):
    db = get_db()
    db.execute(
        "UPDATE sections SET number = ?, title = ?, description = ?, background = ? WHERE id = ?",
        (number, title, description, background, section_id),
    )
    db.commit()


def delete_section(section_id):
    db = get_db()
    section = db.execute("SELECT * FROM sections WHERE id = ?", (section_id,)).fetchone()
    if not section:
        return False

    course_id = section["course_id"]
    lessons = db.execute("SELECT id FROM lessons WHERE section_id = ?", (section_id,)).fetchall()
    if lessons:
        prev = db.execute(
            "SELECT id FROM sections WHERE course_id = ? AND number < ? ORDER BY number DESC LIMIT 1",
            (course_id, section["number"])
        ).fetchone()
        
        if not prev:
            return False
            
        db.execute(
            "UPDATE lessons SET section_id = ? WHERE section_id = ?",
            (prev["id"], section_id)
        )
        _reorder_all_lessons_in_course(course_id)
    
    db.execute("DELETE FROM sections WHERE id = ?", (section_id,))
    
    remaining_sections = db.execute(
        "SELECT id FROM sections WHERE course_id = ? ORDER BY number",
        (course_id,)
    ).fetchall()
    for idx, s in enumerate(remaining_sections, start=1):
        db.execute("UPDATE sections SET number = ? WHERE id = ?", (idx, s["id"]))
        
    db.commit()
    return True


def _reorder_all_lessons_in_course(course_id):
    db = get_db()
    lessons = db.execute("""
        SELECT l.id 
        FROM lessons l
        LEFT JOIN sections s ON l.section_id = s.id
        WHERE l.course_id = ?
        ORDER BY CASE WHEN s.number IS NULL THEN 0 ELSE s.number END ASC, l.number ASC
    """, (course_id,)).fetchall()
    
    for lid in lessons:
        db.execute("UPDATE lessons SET number = number + 10000 WHERE id = ?", (lid["id"],))
    
    for idx, lid in enumerate(lessons, start=1):
        db.execute("UPDATE lessons SET number = ? WHERE id = ?", (idx, lid["id"]))
    db.commit()


def update_section_order(section_id, number):
    db = get_db()
    db.execute("UPDATE sections SET number = ? WHERE id = ?", (number, section_id))
    db.commit()


# ─── Activity Queries ────────────────────────────────────────────────────────

def award_xp(user_id, xp_amount, activity_type, course_id=None):
    db = get_db()
    db.execute(
        "INSERT INTO activity_log (user_id, course_id, activity_type, xp_amount) VALUES (?, ?, ?, ?)",
        (user_id, course_id, activity_type, xp_amount),
    )
    db.execute(
        "UPDATE users SET total_xp = total_xp + ? WHERE id = ?",
        (xp_amount, user_id),
    )
    db.commit()
    return xp_amount


def deduct_xp(user_id, xp_amount, activity_type):
    db = get_db()
    user = get_user_by_id(user_id)
    if not user or user["total_xp"] < xp_amount:
        return False

    db.execute(
        "INSERT INTO activity_log (user_id, activity_type, xp_amount) VALUES (?, ?, ?)",
        (user_id, activity_type, -xp_amount),
    )
    db.execute(
        "UPDATE users SET total_xp = total_xp - ? WHERE id = ?",
        (xp_amount, user_id),
    )
    db.commit()
    return True


def get_user_stats(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return None
    return {"total_xp": user["total_xp"]}


def update_user_profile(user_id, name):
    db = get_db()
    db.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
    db.commit()


def delete_user(user_id):
    db = get_db()
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()


def get_lesson_by_id(lesson_id):
    return get_db().execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone()


def get_lessons_by_course(course_id):
    return get_db().execute(
        "SELECT * FROM lessons WHERE course_id = ? ORDER BY number", (course_id,)
    ).fetchall()


def get_lesson_by_course_and_number(course_id, number):
    return get_db().execute(
        "SELECT * FROM lessons WHERE course_id = ? AND number = ?", (course_id, number)
    ).fetchone()


def create_lesson(course_id, number, slug, title, summary, content, route_name=None, content_type='html', section_id=None, builder_json=None, plan_json=None):
    db = get_db()
    db.execute(
        """
        INSERT INTO lessons (course_id, number, slug, title, summary, content, route_name, content_type, section_id, builder_json, plan_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (course_id, number, slug, title, summary, content, route_name, content_type, section_id, builder_json, plan_json),
    )
    db.commit()
    return db.execute(
        "SELECT * FROM lessons WHERE course_id = ? AND number = ?", (course_id, number)
    ).fetchone()


def update_lesson(lesson_id, number, slug, title, summary, content, route_name=None, content_type='html', section_id=None, builder_json=None, plan_json=None):
    db = get_db()
    db.execute(
        """
        UPDATE lessons SET number = ?, slug = ?, title = ?, summary = ?, content = ?,
               route_name = ?, content_type = ?, section_id = ?, builder_json = ?, plan_json = ?
        WHERE id = ?
        """,
        (number, slug, title, summary, content, route_name, content_type, section_id, builder_json, plan_json, lesson_id),
    )
    db.commit()


def update_lesson_section_and_order(lesson_id, section_id, number):
    db = get_db()
    db.execute(
        "UPDATE lessons SET section_id = ?, number = ? WHERE id = ?",
        (section_id, number, lesson_id),
    )
    db.commit()


def reorder_sections(course_id, section_ids):
    db = get_db()
    for sid in section_ids:
        db.execute("UPDATE sections SET number = number + 1000 WHERE id = ?", (sid,))
    for idx, sid in enumerate(section_ids, start=1):
        db.execute("UPDATE sections SET number = ? WHERE id = ?", (idx, sid))
    db.commit()


def reorder_lessons(course_id, section_id, lesson_ids):
    db = get_db()
    for lid in lesson_ids:
        db.execute("UPDATE lessons SET section_id = ? WHERE id = ?", (section_id, lid))

    base = 100000
    for idx, lid in enumerate(lesson_ids, start=1):
        db.execute("UPDATE lessons SET number = ? WHERE id = ?", (base + idx, lid))

    _reorder_all_lessons_in_course(course_id)
    db.commit()


def delete_lesson(lesson_id):
    db = get_db()
    lesson = db.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    if lesson is None:
        return False

    course_id = lesson["course_id"]
    deleted_number = lesson["number"]

    remaining = db.execute(
        "SELECT * FROM lessons WHERE course_id = ? AND id != ? ORDER BY number",
        (course_id, lesson_id),
    ).fetchall()

    if remaining:
        fallback = remaining[0]
        for r in remaining:
            if r["number"] > deleted_number:
                fallback = r
                break

        db.execute(
            "UPDATE progress SET current_lesson_id = ? WHERE current_lesson_id = ?",
            (fallback["id"], lesson_id),
        )

        new_total = len(remaining)
        db.execute(
            """
            UPDATE progress
            SET completed_lessons = MIN(completed_lessons, ?)
            WHERE course_id = ?
            """,
            (new_total, course_id),
        )
    else:
        db.execute("DELETE FROM progress WHERE course_id = ?", (course_id,))

    db.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
    _reorder_all_lessons_in_course(course_id)
    db.commit()
    return True


# ─── Job Tracking Queries ───────────────────────────────────────────────────

def create_system_job(job_id, status='pending', progress=0, title=None, url=None):
    db = get_db()
    db.execute(
        "INSERT INTO system_jobs (job_id, status, progress_percent, current_title, result_url) VALUES (?, ?, ?, ?, ?)",
        (job_id, status, progress, title, url)
    )
    db.commit()


def update_system_job(job_id, status=None, progress=None, title=None, url=None, error=None):
    db = get_db()
    fields = []
    params = []
    
    if status is not None:
        fields.append("status = ?")
        params.append(status)
    if progress is not None:
        fields.append("progress_percent = ?")
        params.append(progress)
    if title is not None:
        fields.append("current_title = ?")
        params.append(title)
    if url is not None:
        fields.append("result_url = ?")
        params.append(url)
    if error is not None:
        fields.append("error_message = ?")
        params.append(error)
        
    if not fields:
        return

    fields.append("updated_at = CURRENT_TIMESTAMP")
    query = f"UPDATE system_jobs SET {', '.join(fields)} WHERE job_id = ?"
    params.append(job_id)
    
    db.execute(query, params)
    db.commit()


def get_system_job(job_id):
    return get_db().execute("SELECT * FROM system_jobs WHERE job_id = ?", (job_id,)).fetchone()


def delete_system_job(job_id):
    db = get_db()
    db.execute("DELETE FROM system_jobs WHERE job_id = ?", (job_id,))
    db.commit()


def mark_lesson_complete(user_id, course_slug, completed_lesson_number):
    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE slug = ?", (course_slug,)).fetchone()
    if course is None:
        return None

    lessons = db.execute(
        "SELECT * FROM lessons WHERE course_id = ? ORDER BY number",
        (course["id"],),
    ).fetchall()
    if not lessons:
        return None

    progress = get_progress(user_id, course["id"])
    if progress is None:
        return None

    is_new_completion = completed_lesson_number > progress["completed_lessons"]

    next_lesson = None
    for lesson in lessons:
        if lesson["number"] == completed_lesson_number + 1:
            next_lesson = lesson
            break

    if next_lesson is None:
        next_lesson = lessons[-1]

    db.execute(
        """
        UPDATE progress
        SET completed_lessons = MAX(completed_lessons, ?),
            current_lesson_id = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (completed_lesson_number, next_lesson["id"], progress["id"]),
    )
    db.commit()

    awards = []
    if is_new_completion:
        award_xp(user_id, 10, 'lesson_complete', course_id=course["id"])
        awards.append({'type': 'Lesson Completed', 'xp': 10})
        
        current_lesson = next((l for l in lessons if l["number"] == completed_lesson_number), None)
        if current_lesson and current_lesson["section_id"]:
            section_lessons = [l for l in lessons if l["section_id"] == current_lesson["section_id"]]
            last_in_section = max(section_lessons, key=lambda l: l["number"])
            if completed_lesson_number == last_in_section["number"]:
                awards.append({'type': 'Chapter Completed', 'xp': 50})
                award_xp(user_id, 50, 'chapter_complete', course_id=course["id"])

        if completed_lesson_number == lessons[-1]["number"]:
            awards.append({'type': 'Course Completed', 'xp': 200})
            award_xp(user_id, 200, 'course_complete', course_id=course["id"])
    
    return awards