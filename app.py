import os
import re
from functools import wraps

import markdown
from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
    abort,
)
from werkzeug.security import check_password_hash, generate_password_hash

import database


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["DATABASE"] = os.path.join(app.instance_path, "learn_with_kabeer.sqlite3")


# ─── Helpers ────────────────────────────────────────────────────────────────


def lesson_url(lesson, course_slug=None):
    """Generate URL for a lesson. Every saved lesson is viewable."""
    if not course_slug:
        course = database.get_course_by_id(lesson["course_id"])
        course_slug = course["slug"] if course else "unknown"
    return url_for("lesson_view", course_slug=course_slug, lesson_number=lesson["number"])


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Sign in to save your progress.", "info")
            return redirect(url_for("login", next=request.path))
        return view(**kwargs)
    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None or not g.user["is_admin"]:
            abort(403)
        return view(**kwargs)
    return wrapped_view


@app.template_filter('markdown')
def render_markdown(text):
    if text is None:
        return ""
    html = markdown.markdown(text, extensions=['fenced_code', 'tables'])

    def replace_code_block(match):
        lang_class = match.group(1) or ""
        code_content = match.group(2)

        lang = "Terminal"
        icon = "terminal"
        border_color = "border-[#2A2925]"
        header_text_color = "text-[#C8C0B3]"
        header_extra = ""

        if lang_class.startswith("language-"):
            lang = lang_class.replace("language-", "")

        if lang.lower() in ["python", "py"]:
            lang = "Python"
            icon = "code-2"
            border_color = "border-gold-500"
            header_text_color = "text-gold-100"
            header_extra = '<span class="rounded-md border border-gold-500/50 px-2 py-1 text-[11px] font-semibold text-gold-100">Clean</span>'
        elif lang.lower() in ["javascript", "js"]:
            lang = "JavaScript"
            icon = "code-2"
        elif lang.lower() in ["c#", "csharp"]:
            lang = "C#"
            icon = "code-2"
        elif lang.lower() == "html":
            lang = "HTML"
            icon = "code-2"
        elif lang.lower() == "css":
            lang = "CSS"
            icon = "code-2"
        elif lang.lower() in ["bash", "sh", "terminal"]:
            lang = "Terminal"
            icon = "terminal"
        else:
            if lang != "Terminal":
                lang = lang.capitalize()

        return f'''<div class="overflow-hidden rounded-xl border {border_color} bg-[#151412] my-8 not-prose">
    <div class="flex items-center justify-between border-b border-[#2A2925] px-4 py-3">
        <span class="text-xs font-semibold {header_text_color}">{lang}</span>
        {header_extra if header_extra else f'<i data-lucide="{icon}" class="w-4 h-4 text-[#8E8577]"></i>'}
    </div>
    <div class="overflow-x-auto p-5">
        <pre class="font-mono text-[13px] leading-7 text-[#E8E1D6]"><code>{code_content}</code></pre>
    </div>
</div>'''

    html = re.sub(r'<pre><code(?: class="([^"]+)")?>(.*?)</code></pre>', replace_code_block, html, flags=re.DOTALL)

    def replace_blockquote(match):
        content = match.group(1).strip()

        is_warning = False
        if re.match(r'^<p>(?:<strong>)?(?:Warning|Important|Alert):?(?:</strong>)?\s*', content, re.IGNORECASE):
            is_warning = True
            content = re.sub(r'^<p>(?:<strong>)?(?:Warning|Important|Alert):?(?:</strong>)?\s*', '<p>', content, flags=re.IGNORECASE)

        icon = "alert-triangle" if is_warning else "info"

        return f'''<div class="my-10 rounded-xl border border-line bg-paper p-5 not-prose">
    <div class="flex gap-4">
        <span class="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-gold-100 bg-gold-50 text-gold-600">
            <i data-lucide="{icon}" class="w-4 h-4"></i>
        </span>
        <div class="text-sm leading-7 text-muted prose-p:my-0 prose-strong:font-semibold prose-strong:text-ink">
            {content}
        </div>
    </div>
</div>'''

    html = re.sub(r'<blockquote>(.*?)</blockquote>', replace_blockquote, html, flags=re.DOTALL)

    return html


# ─── Request Hooks ──────────────────────────────────────────────────────────


@app.before_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = database.get_user_by_id(user_id) if user_id else None


@app.context_processor
def inject_template_helpers():
    return {
        "current_user": g.get("user"),
        "lesson_url": lesson_url,
    }


# ─── Public Routes ──────────────────────────────────────────────────────────


@app.route("/")
def home():
    if g.user:
        return render_template("index.html", **database.get_course_overview(g.user))
    return render_template("index.html", **database.get_course_overview())


@app.route("/courses")
def courses():
    return render_template("courses/index.html", courses=database.get_course_library(g.user))


@app.route("/course/<course_slug>")
def course_overview(course_slug):
    overview = database.get_course_overview(g.user, course_slug)
    if not overview["course"]:
        abort(404)
    return render_template("courses/overview.html", **overview)


@app.route("/course/<course_slug>/enroll", methods=("POST",))
@login_required
def enroll_course(course_slug):
    progress = database.enroll_user_in_course(g.user["id"], course_slug)
    if progress is None:
        flash("This course is not open for enrollment yet, or has no lessons.", "error")
        return redirect(url_for("courses"))

    overview = database.get_course_overview(g.user, course_slug)
    if overview["current_lesson"]:
        flash("You are enrolled. Your progress will be saved from here.", "success")
        return redirect(lesson_url(overview["current_lesson"], course_slug))

    flash("You are enrolled.", "success")
    return redirect(url_for("course_overview", course_slug=course_slug))


# ─── Auth Routes ────────────────────────────────────────────────────────────


@app.route("/signup", methods=("GET", "POST"))
def signup():
    if g.user:
        return redirect(url_for("home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        error = None
        if not name:
            error = "Please enter your name."
        elif not email:
            error = "Please enter your email."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."

        if error is None:
            try:
                user = database.create_user(name, email, generate_password_hash(password))
            except database.DuplicateEmailError:
                error = "An account with that email already exists."
            else:
                session.clear()
                session["user_id"] = user["id"]
                flash("Your account is ready. Choose a course to enroll and start tracking progress.", "success")
                return redirect(url_for("courses"))

        flash(error, "error")

    return render_template("auth/signup.html")


@app.route("/login", methods=("GET", "POST"))
def login():
    if g.user:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = database.get_user_by_email(email)

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Email or password is incorrect.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            flash("Welcome back.", "success")
            return redirect(request.args.get("next") or url_for("home"))

    return render_template("auth/login.html")


@app.route("/logout", methods=("POST",))
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("home"))


# ─── Lesson Routes ──────────────────────────────────────────────────────────


@app.route("/course/<course_slug>/lesson/<int:lesson_number>")
@login_required
def lesson_view(course_slug, lesson_number):
    overview = database.get_course_overview(g.user, course_slug)
    if not overview["course"] or not overview["enrolled"]:
        flash("Enroll in the course before starting lessons.", "info")
        return redirect(url_for("course_overview", course_slug=course_slug))

    lesson = database.get_lesson_by_course_and_number(overview["course"]["id"], lesson_number)
    if not lesson:
        abort(404)

    return render_template("lessons/dynamic_lesson.html", lesson=lesson, **overview)


@app.route("/course/<course_slug>/lesson/<int:lesson_number>/complete", methods=("POST",))
@login_required
def complete_lesson(course_slug, lesson_number):
    if not database.mark_lesson_complete(g.user["id"], course_slug, lesson_number):
        flash("Enroll in the course before saving lesson progress.", "info")
        return redirect(url_for("course_overview", course_slug=course_slug))

    flash("Lesson marked complete. Your progress was saved.", "success")
    return redirect(url_for("course_overview", course_slug=course_slug))


# ─── Admin Routes ───────────────────────────────────────────────────────────


@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    courses = database.get_course_library(g.user)
    return render_template("admin/dashboard.html", courses=courses)


@app.route("/admin/courses/new", methods=("GET", "POST"))
@login_required
@admin_required
def admin_course_new():
    if request.method == "POST":
        title = request.form["title"].strip()
        slug = request.form["slug"].strip().lower()
        subtitle = request.form["subtitle"].strip()
        level = request.form["level"]
        status = request.form["status"]

        if not title or not slug or not subtitle:
            flash("All fields are required.", "error")
            return render_template("admin/course_form.html", course=None)

        try:
            database.create_course(slug, title, subtitle, level, status)
            flash("Course created successfully.", "success")
        except Exception:
            flash("A course with this slug already exists.", "error")
            return render_template("admin/course_form.html", course=None)

        return redirect(url_for("admin_dashboard"))

    return render_template("admin/course_form.html", course=None)


@app.route("/admin/courses/<int:course_id>/edit", methods=("GET", "POST"))
@login_required
@admin_required
def admin_course_edit(course_id):
    course = database.get_course_by_id(course_id)
    if not course:
        abort(404)

    if request.method == "POST":
        title = request.form["title"].strip()
        slug = request.form["slug"].strip().lower()
        subtitle = request.form["subtitle"].strip()
        level = request.form["level"]
        status = request.form["status"]

        database.update_course(course_id, slug, title, subtitle, level, status)
        flash("Course updated successfully.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/course_form.html", course=course)


@app.route("/admin/courses/<int:course_id>/delete", methods=("POST",))
@login_required
@admin_required
def admin_course_delete(course_id):
    course = database.get_course_by_id(course_id)
    if not course:
        abort(404)

    affected = database.delete_course(course_id)
    if affected > 0:
        flash(f"Course \"{course['title']}\" deleted. {affected} enrolled user(s) were unenrolled.", "success")
    else:
        flash(f"Course \"{course['title']}\" deleted.", "success")
    return redirect(url_for("admin_dashboard"))


# ─── Admin Section Routes ───────────────────────────────────────────────────


@app.route("/admin/courses/<int:course_id>/sections/new", methods=("GET", "POST"))
@login_required
@admin_required
def admin_section_new(course_id):
    course = database.get_course_by_id(course_id)
    if not course:
        abort(404)

    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        
        # Auto-assign next number
        existing = database.get_sections_by_course(course_id)
        next_num = max((s["number"] for s in existing), default=0) + 1

        if not title:
            flash("Title is required.", "error")
        else:
            database.create_section(course_id, next_num, title, description)
            flash("Section created.", "success")
            return redirect(url_for("admin_dashboard"))

    return render_template("admin/section_form.html", course=course, section=None)


@app.route("/admin/sections/<int:section_id>/edit", methods=("GET", "POST"))
@login_required
@admin_required
def admin_section_edit(section_id):
    section = database.get_section_by_id(section_id)
    if not section:
        abort(404)
    course = database.get_course_by_id(section["course_id"])

    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        number = int(request.form["number"])

        if not title:
            flash("Title is required.", "error")
        else:
            database.update_section(section_id, number, title, description)
            flash("Section updated.", "success")
            return redirect(url_for("admin_dashboard"))

    return render_template("admin/section_form.html", course=course, section=section)


@app.route("/admin/sections/<int:section_id>/delete", methods=("POST",))
@login_required
@admin_required
def admin_section_delete(section_id):
    section = database.get_section_by_id(section_id)
    if not section:
        abort(404)
    database.delete_section(section_id)
    flash("Section deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/courses/<int:course_id>/lessons/new", methods=("GET", "POST"))
@login_required
@admin_required
def admin_lesson_new(course_id):
    course = database.get_course_by_id(course_id)
    if not course:
        abort(404)
    sections = database.get_sections_by_course(course_id)

    if request.method == "POST":
        title = request.form["title"].strip()
        slug = request.form["slug"].strip().lower()
        summary = request.form["summary"].strip()
        content = request.form.get("content", "").strip()
        content_type = request.form.get("content_type", "html")
        section_id = request.form.get("section_id")
        section_id = int(section_id) if section_id else None

        # Auto-assign next available number
        existing_lessons = database.get_lessons_by_course(course_id)
        next_number = max((l["number"] for l in existing_lessons), default=0) + 1

        if not title or not slug or not summary:
            flash("Title, slug, and summary are required.", "error")
            return render_template("admin/lesson_form.html", course=course, lesson=None, sections=sections)

        try:
            database.create_lesson(course_id, next_number, slug, title, summary, content, None, content_type, section_id)
            flash(f"Lesson {next_number} created successfully.", "success")
        except Exception as e:
            flash(f"Error creating lesson: {e}", "error")
            return render_template("admin/lesson_form.html", course=course, lesson=None, sections=sections)

        return redirect(url_for("admin_dashboard"))

    return render_template("admin/lesson_form.html", course=course, lesson=None, sections=sections)


@app.route("/admin/lessons/<int:lesson_id>/edit", methods=("GET", "POST"))
@login_required
@admin_required
def admin_lesson_edit(lesson_id):
    lesson = database.get_lesson_by_id(lesson_id)
    if not lesson:
        abort(404)

    course = database.get_course_by_id(lesson["course_id"])
    sections = database.get_sections_by_course(course["id"])

    if request.method == "POST":
        title = request.form["title"].strip()
        slug = request.form["slug"].strip().lower()
        number = int(request.form["number"])
        summary = request.form["summary"].strip()
        content = request.form.get("content", "").strip()
        content_type = request.form.get("content_type", "html")
        section_id = request.form.get("section_id")
        section_id = int(section_id) if section_id else None

        database.update_lesson(lesson_id, number, slug, title, summary, content, None, content_type, section_id)
        flash("Lesson updated successfully.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/lesson_form.html", course=course, lesson=lesson, sections=sections)


@app.route("/admin/lessons/<int:lesson_id>/delete", methods=("POST",))
@login_required
@admin_required
def admin_lesson_delete(lesson_id):
    lesson = database.get_lesson_by_id(lesson_id)
    if not lesson:
        abort(404)

    database.delete_lesson(lesson_id)
    flash(f"Lesson \"{lesson['title']}\" deleted and remaining lessons renumbered.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/sections/reorder", methods=("POST",))
@login_required
@admin_required
def admin_sections_reorder():
    data = request.json
    # data: { course_id: 1, section_ids: [1, 2, 3] }
    course_id = data.get("course_id")
    section_ids = data.get("section_ids", [])
    
    for idx, sid in enumerate(section_ids, start=1):
        database.update_section_order(sid, idx)
    
    return {"status": "success"}


@app.route("/admin/lessons/reorder", methods=("POST",))
@login_required
@admin_required
def admin_lessons_reorder():
    data = request.json
    # data: { course_id: 1, section_id: 2, lesson_ids: [10, 11] }
    course_id = data.get("course_id")
    section_id = data.get("section_id")
    lesson_ids = data.get("lesson_ids", [])
    
    # section_id could be None (unassigned)
    if section_id == "null": section_id = None

    for idx, lid in enumerate(lesson_ids, start=1):
        # We need a new database helper for this or use update_lesson
        database.update_lesson_section_and_order(lid, section_id, idx)
    
    return {"status": "success"}


# ─── Init ───────────────────────────────────────────────────────────────────


database.init_app(app)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
