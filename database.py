import os
import sqlite3

from flask import current_app, g


class DuplicateEmailError(Exception):
    pass


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(current_app.instance_path, exist_ok=True)
    db = sqlite3.connect(current_app.config["DATABASE"])
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            subtitle TEXT NOT NULL,
            level TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            number INTEGER NOT NULL,
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
            UNIQUE (course_id, number)
        );

        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            section_id INTEGER,
            number INTEGER NOT NULL,
            slug TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            route_name TEXT,
            content TEXT,
            content_type TEXT NOT NULL DEFAULT 'html',
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
            FOREIGN KEY (section_id) REFERENCES sections (id) ON DELETE SET NULL,
            UNIQUE (course_id, number)
        );

        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            current_lesson_id INTEGER NOT NULL,
            completed_lessons INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
            FOREIGN KEY (current_lesson_id) REFERENCES lessons (id) ON DELETE SET NULL,
            UNIQUE (user_id, course_id)
        );
        """
    )

    # Migration: add content_type column if missing (for older databases)
    try:
        db.execute("ALTER TABLE lessons ADD COLUMN content_type TEXT NOT NULL DEFAULT 'html'")
        db.commit()
    except sqlite3.OperationalError:
        pass

    # Migration: add section_id column if missing
    try:
        db.execute("ALTER TABLE lessons ADD COLUMN section_id INTEGER REFERENCES sections(id) ON DELETE SET NULL")
        db.commit()
    except sqlite3.OperationalError:
        pass

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
    except sqlite3.IntegrityError as exc:
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


# ─── Course Queries ─────────────────────────────────────────────────────────


def get_course_by_id(course_id):
    return get_db().execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()


def get_course_library(user=None):
    db = get_db()
    courses = db.execute(
        """
        SELECT c.*,
               (SELECT COUNT(*) FROM lessons WHERE course_id = c.id) AS total_lessons,
               (SELECT COUNT(*) FROM progress WHERE course_id = c.id) AS enrolled_count
        FROM courses c
        ORDER BY
            CASE c.status WHEN 'active' THEN 0 ELSE 1 END,
            c.id
        """
    ).fetchall()

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

        # Organize lessons into sections for the admin view
        grouped_sections = []
        for s in sections_raw:
            sec_lessons = [dict(l) for l in lessons if l["section_id"] == s["id"]]
            grouped_sections.append({
                "id": s["id"],
                "title": s["title"],
                "description": s["description"],
                "number": s["number"],
                "lessons": sec_lessons
            })

        # Add unassigned lessons to a virtual section if any exist
        misc_lessons = [dict(l) for l in lessons if l["section_id"] is None]
        if misc_lessons:
            grouped_sections.append({
                "id": None,
                "title": "Unassigned Lessons",
                "description": "Lessons not assigned to any section",
                "number": 999,
                "lessons": misc_lessons
            })

        # If absolutely no sections (e.g. legacy data), ensure at least one entry for UI
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


def get_course_overview(user=None, course_slug="python"):
    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE slug = ?", (course_slug,)).fetchone()
    if course is None:
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

    # Organize lessons into sections
    sections = []
    
    # 1. Handle unassigned lessons FIRST (at the start of the course)
    misc_lessons = [dict(l) for l in lessons if l["section_id"] is None]
    if misc_lessons:
        sections.append({
            "id": None,
            "title": "Unit 1" if not sections_raw else "Getting Started",
            "description": "The fundamentals of this path",
            "number": 0,
            "lessons": misc_lessons
        })

    # 2. Add defined sections
    for s in sections_raw:
        sec_lessons = [dict(l) for l in lessons if l["section_id"] == s["id"]]
        sections.append({
            "id": s["id"],
            "title": s["title"],
            "description": s["description"],
            "number": s["number"],
            "lessons": sec_lessons
        })

    # If no lessons at all, ensures sections is empty
    if not lessons and not sections_raw:
        sections = []

    # Enrich course object with dynamic stats
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


def create_course(slug, title, subtitle, level, status):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO courses (slug, title, subtitle, level, status) VALUES (?, ?, ?, ?, ?)",
        (slug, title, subtitle, level, status),
    )
    course_id = cursor.lastrowid
    
    # Create a default "Curriculum" section
    db.execute(
        "INSERT INTO sections (course_id, number, title, description) VALUES (?, ?, ?, ?)",
        (course_id, 1, "Curriculum", "Main course content")
    )
    
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
    """Delete a course and cascade-clean all related data."""
    db = get_db()

    # Count affected users for feedback
    affected = db.execute(
        "SELECT COUNT(*) AS cnt FROM progress WHERE course_id = ?", (course_id,)
    ).fetchone()["cnt"]

    # Delete progress rows for this course
    db.execute("DELETE FROM progress WHERE course_id = ?", (course_id,))
    # Delete lessons for this course
    db.execute("DELETE FROM lessons WHERE course_id = ?", (course_id,))
    # Delete the course itself
    db.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    db.commit()

    return affected


# ─── Section Queries ────────────────────────────────────────────────────────


def get_sections_by_course(course_id):
    return get_db().execute(
        "SELECT * FROM sections WHERE course_id = ? ORDER BY number", (course_id,)
    ).fetchall()


def get_section_by_id(section_id):
    return get_db().execute("SELECT * FROM sections WHERE id = ?", (section_id,)).fetchone()


def create_section(course_id, number, title, description):
    db = get_db()
    db.execute(
        "INSERT INTO sections (course_id, number, title, description) VALUES (?, ?, ?, ?)",
        (course_id, number, title, description),
    )
    db.commit()
    return db.execute(
        "SELECT * FROM sections WHERE course_id = ? AND number = ?", (course_id, number)
    ).fetchone()


def update_section(section_id, number, title, description):
    db = get_db()
    db.execute(
        "UPDATE sections SET number = ?, title = ?, description = ? WHERE id = ?",
        (number, title, description, section_id),
    )
    db.commit()


def delete_section(section_id):
    db = get_db()
    db.execute("DELETE FROM sections WHERE id = ?", (section_id,))
    db.commit()


def update_section_order(section_id, number):
    db = get_db()
    db.execute("UPDATE sections SET number = ? WHERE id = ?", (number, section_id))
    db.commit()


# ─── Lesson Queries ─────────────────────────────────────────────────────────


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


def create_lesson(course_id, number, slug, title, summary, content, route_name=None, content_type='html', section_id=None):
    db = get_db()
    db.execute(
        """
        INSERT INTO lessons (course_id, number, slug, title, summary, content, route_name, content_type, section_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (course_id, number, slug, title, summary, content, route_name, content_type, section_id),
    )
    db.commit()
    return db.execute(
        "SELECT * FROM lessons WHERE course_id = ? AND number = ?", (course_id, number)
    ).fetchone()


def update_lesson(lesson_id, number, slug, title, summary, content, route_name=None, content_type='html', section_id=None):
    db = get_db()
    db.execute(
        """
        UPDATE lessons SET number = ?, slug = ?, title = ?, summary = ?, content = ?,
               route_name = ?, content_type = ?, section_id = ?
        WHERE id = ?
        """,
        (number, slug, title, summary, content, route_name, content_type, section_id, lesson_id),
    )
    db.commit()


def update_lesson_section_and_order(lesson_id, section_id, number):
    db = get_db()
    db.execute(
        "UPDATE lessons SET section_id = ?, number = ? WHERE id = ?",
        (section_id, number, lesson_id),
    )
    db.commit()


def delete_lesson(lesson_id):
    """Delete a lesson and fix progress for any enrolled users."""
    db = get_db()

    lesson = db.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    if lesson is None:
        return False

    course_id = lesson["course_id"]
    deleted_number = lesson["number"]

    # Get remaining lessons (excluding the one being deleted)
    remaining = db.execute(
        "SELECT * FROM lessons WHERE course_id = ? AND id != ? ORDER BY number",
        (course_id, lesson_id),
    ).fetchall()

    if remaining:
        # Find the best fallback lesson for users who were on the deleted lesson
        fallback = remaining[0]
        for r in remaining:
            if r["number"] > deleted_number:
                fallback = r
                break

        # Update progress: users pointing to deleted lesson → move to fallback
        db.execute(
            "UPDATE progress SET current_lesson_id = ? WHERE current_lesson_id = ?",
            (fallback["id"], lesson_id),
        )

        # Cap completed_lessons so it doesn't exceed new total count
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
        # No remaining lessons — remove all progress for this course
        db.execute("DELETE FROM progress WHERE course_id = ?", (course_id,))

    # Delete the lesson
    db.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))

    # Renumber remaining lessons sequentially (1, 2, 3...)
    remaining_after = db.execute(
        "SELECT id FROM lessons WHERE course_id = ? ORDER BY number",
        (course_id,),
    ).fetchall()
    for idx, row in enumerate(remaining_after, start=1):
        db.execute("UPDATE lessons SET number = ? WHERE id = ?", (idx, row["id"]))

    db.commit()
    return True


def mark_lesson_complete(user_id, course_slug, completed_lesson_number):
    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE slug = ?", (course_slug,)).fetchone()
    if course is None:
        return False

    lessons = db.execute(
        "SELECT * FROM lessons WHERE course_id = ? ORDER BY number",
        (course["id"],),
    ).fetchall()
    if not lessons:
        return False

    progress = get_progress(user_id, course["id"])
    if progress is None:
        return False

    # Find next lesson; if none exists, stay on the current (last) lesson
    next_lesson = None
    for lesson in lessons:
        if lesson["number"] == completed_lesson_number + 1:
            next_lesson = lesson
            break

    if next_lesson is None:
        # Completed the last lesson — stay on it
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
    return True
