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


def get_available_backgrounds():
    """List available backgrounds from the static folder."""
    bg_dir = os.path.join(app.static_folder, "imgs/assets/background")
    if not os.path.exists(bg_dir):
        return []
    return [f for f in os.listdir(bg_dir) if f.endswith(('.png', '.jpg', '.jpeg', '.gif'))]


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
        if lang_class.startswith("language-"):
            lang = lang_class.replace("language-", "")

        if lang.lower() in ["python", "py"]:
            lang = "Python"
            icon = "code-2"
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

        # Split lines to add line numbers
        lines = code_content.strip().split('\n')
        line_numbers_html = "".join([f'<span class="opacity-30">{i+1}</span>' for i in range(len(lines))])
        
        import html as html_lib
        safe_code = html_lib.escape(code_content.strip())
        code_lines_html = "".join([f'<div class="px-4 hover:bg-white/5 transition-colors">{html_lib.escape(line) if line else "&nbsp;"}</div>' for line in lines])

        return f'''<div class="relative overflow-hidden rounded-xl border border-[#2A2A2A] bg-[#1C1C1C] shadow-2xl my-10 not-prose group">
    <div class="flex items-center justify-between border-b border-[#2A2A2A] bg-[#1C1C1C] px-5 py-3.5">
        <div class="flex items-center gap-4">
            <div class="flex gap-1.5">
                <div class="h-2.5 w-2.5 rounded-full bg-[#333333]"></div>
                <div class="h-2.5 w-2.5 rounded-full bg-[#333333]"></div>
                <div class="h-2.5 w-2.5 rounded-full bg-[#333333]"></div>
            </div>
            <div class="h-4 w-[1px] bg-[#2A2A2A]"></div>
            <span class="text-[11px] font-bold uppercase tracking-widest text-[#6B6B6B] font-mono">{lang.lower()}</span>
        </div>
        <div class="flex items-center gap-4">
            <button onclick="copyToClipboard(this)" data-code="{safe_code}" class="flex items-center gap-2 rounded-md bg-[#2A2A2A] px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider text-[#A3A3A3] transition-all hover:bg-[#333333] hover:text-white focus:outline-none active:scale-95">
                <i data-lucide="copy" class="w-3.5 h-3.5"></i>
                <span class="copy-text">Copy</span>
            </button>
            <i data-lucide="{icon}" class="w-4 h-4 text-[#404040]"></i>
        </div>
    </div>
    
    <div class="flex font-mono text-[13px] leading-[1.8] overflow-x-auto py-5">
        <div class="flex flex-col text-right text-[#6B6B6B] select-none pr-4 border-r border-[#2A2A2A] ml-5 min-w-[2.5rem]">
            {line_numbers_html}
        </div>
        <div class="flex-1 text-[#E5E5E5]">
            {code_lines_html}
        </div>
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
        accent_color = "border-amber-400 bg-amber-50/50 text-amber-900" if is_warning else "border-blue-400 bg-blue-50/50 text-blue-900"
        icon_bg = "bg-amber-100 text-amber-600" if is_warning else "bg-blue-100 text-blue-600"

        return f'''<div class="my-10 rounded-xl border-l-4 {accent_color} px-6 py-5 not-prose shadow-sm">
    <div class="flex gap-4">
        <span class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg {icon_bg}">
            <i data-lucide="{icon}" class="w-4 h-4"></i>
        </span>
        <div class="text-[15px] leading-relaxed prose-p:my-0 prose-strong:font-bold">
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
        if g.user["is_admin"]:
            return redirect(url_for("admin_dashboard"))
        
        # For authenticated users, only show career paths they are enrolled in
        all_paths = database.get_career_paths(g.user["id"])
        career_paths = [p for p in all_paths if p["enrolled"] and p["status"] == "active"]
        
        overview = database.get_course_overview(g.user)
        return render_template("index.html", career_paths=career_paths, **overview)
    
    # For guests, show all active career paths as "Paths to explore"
    career_paths = [p for p in database.get_career_paths() if p["status"] == "active"]
    return render_template("index.html", career_paths=career_paths, **database.get_course_overview())


@app.route("/courses")
def courses():
    return render_template("courses/index.html", courses=database.get_course_library(g.user))


@app.route("/career-paths")
def career_paths():
    paths = database.get_career_paths(g.user["id"] if g.user else None)
    return render_template("career_paths/index.html", paths=paths)


@app.route("/career-paths/<slug>")
def career_path_overview(slug):
    path = database.get_career_path_by_slug(slug, g.user)
    if not path:
        abort(404)
    return render_template("career_paths/overview.html", path=path)


@app.route("/career-paths/<slug>/enroll", methods=("POST",))
@login_required
def enroll_career_path(slug):
    if database.enroll_user_in_career_path(g.user["id"], slug):
        flash("You are now enrolled in this career path.", "success")
    else:
        flash("Could not enroll in this career path.", "error")
    return redirect(url_for("career_path_overview", slug=slug))


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

    # Check if lesson is locked (only for non-admins)
    if not g.user["is_admin"] and lesson_number > overview["completed_lessons"] + 1:
        flash("Complete previous lessons to unlock this one.", "info")
        return redirect(url_for("course_overview", course_slug=course_slug))

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
    career_paths = database.get_career_paths()
    stats = database.get_admin_stats()
    return render_template("admin/dashboard.html", courses=courses, career_paths=career_paths, stats=stats)


@app.route("/admin/courses/<int:course_id>/manage")
@login_required
@admin_required
def admin_course_manage(course_id):
    course = database.get_course_by_id(course_id)
    if not course:
        abort(404)
    # Reuse get_course_overview to get sections and lessons
    overview = database.get_course_overview(g.user, course["slug"])
    return render_template("admin/course_manage.html", **overview)


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


# ─── Admin Career Path Routes ──────────────────────────────────────────────


@app.route("/admin/career-paths/new", methods=("GET", "POST"))
@login_required
@admin_required
def admin_career_path_new():
    if request.method == "POST":
        title = request.form["title"].strip()
        slug = request.form["slug"].strip().lower()
        subtitle = request.form["subtitle"].strip()
        description = request.form["description"].strip()
        level = request.form["level"]
        status = request.form["status"]

        if not title or not slug or not subtitle:
            flash("All fields are required.", "error")
            return render_template("admin/career_path_form.html", path=None)

        try:
            database.create_career_path(slug, title, subtitle, description, level, status)
            flash("Career path created successfully.", "success")
        except Exception:
            flash("A career path with this slug already exists.", "error")
            return render_template("admin/career_path_form.html", path=None)

        return redirect(url_for("admin_dashboard"))

    return render_template("admin/career_path_form.html", path=None)


@app.route("/admin/career-paths/<int:path_id>/edit", methods=("GET", "POST"))
@login_required
@admin_required
def admin_career_path_edit(path_id):
    path = database.get_career_path_by_id(path_id)
    if not path:
        abort(404)

    if request.method == "POST":
        title = request.form["title"].strip()
        slug = request.form["slug"].strip().lower()
        subtitle = request.form["subtitle"].strip()
        description = request.form["description"].strip()
        level = request.form["level"]
        status = request.form["status"]

        if not title or not slug or not subtitle:
            flash("All fields are required.", "error")
            return render_template("admin/career_path_form.html", path=path)

        database.update_career_path(path_id, slug, title, subtitle, description, level, status)
        flash("Career path updated successfully.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/career_path_form.html", path=path)


@app.route("/admin/career-paths/<int:path_id>/manage")
@login_required
@admin_required
def admin_career_path_manage(path_id):
    path = database.get_career_path_by_id(path_id)
    if not path:
        abort(404)

    # Get courses in this path
    path_details = database.get_career_path_by_slug(path["slug"])
    # Get all courses to allow adding existing
    all_courses = database.get_course_library(g.user)

    return render_template("admin/career_path_manage.html", path=path_details, all_courses=all_courses)


@app.route("/admin/career-paths/<int:path_id>/add-course", methods=("POST",))
@login_required
@admin_required
def admin_career_path_add_course(path_id):
    course_id = request.form.get("course_id")
    if course_id:
        database.add_course_to_career_path(path_id, int(course_id))
        flash("Course added to career path.", "success")
    return redirect(url_for("admin_career_path_manage", path_id=path_id))


@app.route("/admin/career-paths/<int:path_id>/remove-course/<int:course_id>", methods=("POST",))
@login_required
@admin_required
def admin_career_path_remove_course(path_id, course_id):
    database.remove_course_from_career_path(path_id, course_id)
    flash("Course removed from career path.", "success")
    return redirect(url_for("admin_career_path_manage", path_id=path_id))


@app.route("/admin/career-paths/reorder", methods=("POST",))
@login_required
@admin_required
def admin_career_path_reorder():
    data = request.json
    path_id = data.get("path_id")
    course_ids = data.get("course_ids", [])
    database.reorder_career_path_courses(path_id, course_ids)
    return {"status": "success"}


@app.route("/admin/career-paths/<int:path_id>/delete", methods=("POST",))
@login_required
@admin_required
def admin_career_path_delete(path_id):
    database.delete_career_path(path_id)
    flash("Career path deleted.", "success")
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
        background = request.form.get("background")
        
        # Auto-assign next number
        existing = database.get_sections_by_course(course_id)
        next_num = max((s["number"] for s in existing), default=0) + 1

        if not title:
            flash("Title is required.", "error")
        else:
            database.create_section(course_id, next_num, title, description, background)
            flash("Section created.", "success")
            return redirect(url_for("admin_dashboard"))

    return render_template("admin/section_form.html", course=course, section=None, backgrounds=get_available_backgrounds())


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
        background = request.form.get("background")

        if not title:
            flash("Title is required.", "error")
        else:
            database.update_section(section_id, number, title, description, background)
            flash("Section updated.", "success")
            return redirect(url_for("admin_dashboard"))

    return render_template("admin/section_form.html", course=course, section=section, backgrounds=get_available_backgrounds())


@app.route("/admin/sections/<int:section_id>/delete", methods=("POST",))
@login_required
@admin_required
def admin_section_delete(section_id):
    section = database.get_section_by_id(section_id)
    if not section:
        abort(404)
    
    course_id = section["course_id"]
    success = database.delete_section(section_id)
    
    if not success:
        flash("Cannot delete section with lessons because there is no previous section to move them to. Please create a section above first.", "error")
    else:
        flash("Section deleted.", "success")
        
    return redirect(url_for("admin_course_manage", course_id=course_id))


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

    database.reorder_sections(course_id, section_ids)

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

    database.reorder_lessons(course_id, section_id, lesson_ids)

    return {"status": "success"}

# ─── Init ───────────────────────────────────────────────────────────────────


database.init_app(app)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
