import os
import re
import json
import time
import threading
from functools import wraps

import markdown
from groq import Groq

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
    jsonify,
)
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv

import database
from ai.generators.blueprint import get_blueprint_system_instruction
from ai.pipelines.course_pipeline import generate_course as ai_generate_course, get_progress as ai_get_progress, clear_progress as ai_clear_progress

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["DATABASE"] = os.path.join(app.instance_path, "learn_with_kabeer.sqlite3")


#  Helpers 


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
    # ... (rest of the markdown logic)
    return html

@app.template_filter('comma')
def comma_filter(value):
    try:
        return "{:,}".format(int(value))
    except (ValueError, TypeError):
        return value


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



#  Request Hooks 


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


#  Public Routes 


@app.route("/")
def home():
    if g.user:
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
    return render_template("courses/index.html", courses=database.get_course_library(g.user, include_private=False))


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

@app.route("/settings", methods=("GET", "POST"))
@login_required
def settings():
    if request.method == "POST":
        name = request.form.get("name")
        
        if not name:
            flash("Name is required.", "error")
        else:
            database.update_user_profile(g.user["id"], name)
            flash("Settings updated successfully.", "success")
            return redirect(url_for("settings"))

    user_stats = database.get_user_stats(g.user["id"])
    return render_template("auth/settings.html", user_stats=user_stats)


@app.route("/settings/delete", methods=("POST",))
@login_required
def delete_account():
    # Final confirmation check could be added here (e.g. password)
    database.delete_user(g.user["id"])
    session.clear()
    flash("Your account has been permanently deleted.", "info")
    return redirect(url_for("home"))


#  Auth Routes 


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


#  Lesson Routes 


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
    awards = database.mark_lesson_complete(g.user["id"], course_slug, lesson_number)
    if awards is None:
        flash("Enroll in the course before saving lesson progress.", "info")
        return redirect(url_for("course_overview", course_slug=course_slug))

    if awards:
        flash(json.dumps(awards), 'xp_award')

    flash("Lesson marked complete. Your progress was saved.", "success")
    return redirect(url_for("course_overview", course_slug=course_slug))


#  Admin Routes 


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
        return redirect(url_for("admin_course_manage", course_id=course_id))

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


#  Admin Career Path Routes 


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
            path = database.create_career_path(slug, title, subtitle, description, level, status)
            flash("Career path created successfully.", "success")
            return redirect(url_for("admin_career_path_manage", path_id=path["id"]))
        except Exception:
            flash("A career path with this slug already exists.", "error")
            return render_template("admin/career_path_form.html", path=None)

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
        return redirect(url_for("admin_career_path_manage", path_id=path_id))

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


#  Admin Section Routes 


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
            return redirect(url_for("admin_course_manage", course_id=course_id))

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
            return redirect(url_for("admin_course_manage", course_id=course["id"]))

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
            lesson = database.create_lesson(course_id, next_number, slug, title, summary, content, None, content_type, section_id)
            flash(f"Lesson {next_number} created successfully.", "success")
            return redirect(url_for("admin_lesson_edit", lesson_id=lesson["id"]))
        except Exception as e:
            flash(f"Error creating lesson: {e}", "error")
            return render_template("admin/lesson_form.html", course=course, lesson=None, sections=sections)

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
        return redirect(url_for("admin_course_manage", course_id=course["id"]))

    return render_template("admin/lesson_form.html", course=course, lesson=lesson, sections=sections)


@app.route("/admin/lessons/<int:lesson_id>/delete", methods=("POST",))
@login_required
@admin_required
def admin_lesson_delete(lesson_id):
    lesson = database.get_lesson_by_id(lesson_id)
    if not lesson:
        abort(404)

    course_id = lesson["course_id"]
    database.delete_lesson(lesson_id)
    flash(f"Lesson \"{lesson['title']}\" deleted and remaining lessons renumbered.", "success")
    return redirect(url_for("admin_course_manage", course_id=course_id))


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


@app.route("/admin/lessons/<int:lesson_id>/builder", methods=("GET", "POST"))
@login_required
@admin_required
def admin_lesson_builder(lesson_id):
    lesson = database.get_lesson_by_id(lesson_id)
    if not lesson:
        abort(404)

    if request.method == "POST":
        content = request.form.get("content", "").strip()
        builder_json = request.form.get("builder_json", "").strip()
        database.update_lesson(lesson_id, lesson["number"], lesson["slug"], lesson["title"], lesson["summary"], content, None, "html", lesson["section_id"], builder_json)
        flash("Lesson layout saved successfully.", "success")
        return redirect(url_for("admin_lesson_builder", lesson_id=lesson_id))

    builder_data = []
    if lesson["builder_json"]:
        try:
            builder_data = json.loads(lesson["builder_json"])
        except json.JSONDecodeError:
            builder_data = []

    course = database.get_course_by_id(lesson["course_id"])
    return render_template("admin/lesson_builder.html", lesson=lesson, course=course, builder_data=builder_data)


@app.route("/admin/upload-image", methods=("POST",))
@login_required
@admin_required
def admin_upload_image():
    if "image" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files["image"]
    lesson_id = request.form.get("lesson_id")
    
    if not file or not lesson_id:
        return jsonify({"error": "Missing file or lesson ID"}), 400

    lesson = database.get_lesson_by_id(lesson_id)
    if not lesson:
        return jsonify({"error": "Lesson not found"}), 404
    
    course = database.get_course_by_id(lesson["course_id"])
    if not course:
        return jsonify({"error": "Course not found"}), 404

    # Construct Path: static/imgs/courses/<course_slug>_<course_id>/<lesson_slug>_<lesson_id>/
    course_folder = f"{course['slug']}_{course['id']}"
    lesson_folder = f"{lesson['slug']}_{lesson['id']}"
    
    upload_dir = os.path.join(
        app.static_folder, "imgs", "courses", course_folder, lesson_folder
    )
    
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)

    from werkzeug.utils import secure_filename
    filename = secure_filename(file.filename)
    
    # Add unique suffix to prevent overwriting
    import time
    name, ext = os.path.splitext(filename)
    filename = f"{name}_{int(time.time())}{ext}"
    
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    # Return relative URL for static loading
    relative_url = f"/static/imgs/courses/{course_folder}/{lesson_folder}/{filename}"
    return jsonify({"url": relative_url})


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


#  Course on Demand (COD) Routes 

SYSTEM_INSTRUCTION_COD = get_blueprint_system_instruction()

@app.route("/cod")
@login_required
def cod_interface():
    # Clear previous COD session state if starting fresh
    if 'cod_state' not in session or request.args.get('reset'):
        session['cod_state'] = {
            'history': [], # List of {"role": "user/assistant", "content": "..."}
            'pending_course': None,
            'total_cost': 0
        }
    return render_template("lessons/cod.html")

@app.route("/cod/chat", methods=("POST",))
@login_required
def cod_chat():
    user_msg = request.json.get("message")
    state = session.get('cod_state')
    
    if not state:
        return {"error": "Session expired"}, 400

    # Prepare chat history for Groq
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION_COD}
    ]
    for msg in state['history']:
        messages.append({"role": msg['role'], "content": msg['content']})
    
    # Add new user message
    state['history'].append({"role": "user", "content": user_msg})
    messages.append({"role": "user", "content": user_msg})

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    try:
        from ai.config import GENERATION_MODEL
        response = client.chat.completions.create(
            model=GENERATION_MODEL,
            response_format={"type": "json_object"},
            messages=messages,
            temperature=0.3
        )
        
        ai_data = json.loads(response.choices[0].message.content)
        ai_message = ai_data.get("message", "I'm processing your request.")
        state['history'].append({"role": "assistant", "content": ai_message})
        
        if ai_data.get("status") == "READY":
            syllabus = ai_data.get("syllabus")
            state['pending_course'] = syllabus
            # Count lessons from sections-based or flat format
            total_lessons = 0
            if syllabus.get('sections'):
                for sec in syllabus['sections']:
                    total_lessons += len(sec.get('lessons', []))
            else:
                total_lessons = len(syllabus.get('lessons', []))
            cost = total_lessons * 3
            state['total_cost'] = cost
            
            can_afford = g.user["is_pro"] or g.user["total_xp"] >= cost
            
            response_msg = f"{ai_message}\n\n"
            response_msg += f"**Course Report & Syllabus:**\n"
            # Handle sections-based or flat lesson lists
            if syllabus.get('sections'):
                for sec in syllabus['sections']:
                    response_msg += f"\n**{sec['title']}**\n"
                    for lesson in sec.get('lessons', []):
                        response_msg += f"- Lesson {lesson.get('number', '?')}: {lesson['title']}\n"
            else:
                for lesson in syllabus.get('lessons', []):
                    response_msg += f"- Lesson {lesson['number']}: {lesson['title']}\n"
            
            response_msg += f"\n**Economic Breakdown:**\n"
            response_msg += f"- Lessons: {total_lessons}\n"
            response_msg += f"- Cost: **{cost:,} XP**\n"
            response_msg += f"- Your Balance: {g.user['total_xp']:,} XP\n"
            
            if not can_afford:
                response_msg += f"\n**Insufficient XP:** You need {cost - g.user['total_xp']:,} more XP to forge this course."
                session['cod_state'] = state
                return {"response": response_msg, "done": True, "needs_confirmation": False, "can_afford": False}
            
            response_msg += "\nEverything is architected. Shall we proceed with content generation?"
            session['cod_state'] = state
            return {"response": response_msg, "done": True, "needs_confirmation": True, "cost": cost, "can_afford": True}
        
        session['cod_state'] = state
        return {"response": ai_message, "done": False}
        
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            return {"error": "rate limit reached, please try again in a minute."}
        print(f"COD Chat Error: {e}")
        return {"error": "something went wrong, please try again."}

@app.route("/cod/confirm", methods=("POST",))
@login_required
def cod_confirm():
    state = session.get('cod_state')
    if not state or 'pending_course' not in state:
        return {"error": "No pending course"}, 400

    cost = state['total_cost']
    if not g.user["is_pro"] and g.user["total_xp"] < cost:
        return {"error": f"Insufficient XP."}, 400

    if not g.user["is_pro"]:
        database.deduct_xp(g.user["id"], cost, "cod_generation")

    # Generate a session ID for progress tracking
    session_id = f"cod-{g.user['id']}-{int(time.time())}"
    session['cod_session_id'] = session_id

    user_id = g.user["id"]
    pending = state['pending_course']

    def _generate_in_background():
        """Run course generation in a background thread."""
        try:
            backgrounds = get_available_backgrounds()
            full_course = ai_generate_course(
                syllabus=pending,
                backgrounds=backgrounds,
                session_id=session_id,
            )

            # Save to database inside app context
            with app.app_context():
                course_slug = session_id
                db_course = database.create_course(
                    slug=course_slug,
                    title=full_course['title'],
                    subtitle=full_course['subtitle'],
                    level=pending.get('level', 'Beginner'),
                    status='active',
                    user_id=user_id,
                )

                sections = {}
                for lesson_data in full_course['lessons']:
                    section_name = lesson_data.get('section', 'Core Curriculum')
                    if section_name not in sections:
                        bg = lesson_data.get('section_background', '')
                        sec = database.create_section(db_course['id'], len(sections)+1, section_name, "", background=bg)
                        sections[section_name] = sec['id']

                    raw_blocks = lesson_data.get('builder_json', [])
                    normalized_blocks = normalize_builder_json(raw_blocks)
                    html_content = builder_json_to_html(normalized_blocks)

                    database.create_lesson(
                        course_id=db_course['id'],
                        number=lesson_data['number'],
                        slug=f"lesson-{lesson_data['number']}-{int(time.time())}",
                        title=lesson_data['title'],
                        summary=lesson_data.get('summary', ""),
                        content=html_content,
                        content_type='html',
                        section_id=sections[section_name],
                        builder_json=json.dumps(normalized_blocks),
                    )

                database.enroll_user_in_course(user_id, course_slug)

                from ai.pipelines.course_pipeline import _update_progress
                _update_progress(session_id, status="complete", url=f"/course/{course_slug}")

        except Exception as e:
            print(f"COD Background Error: {e}")
            from ai.pipelines.course_pipeline import _update_progress
            _update_progress(session_id, status="error", error=str(e))

    # Launch generation in background thread
    thread = threading.Thread(target=_generate_in_background, daemon=True)
    thread.start()

    return {"status": "generating", "session_id": session_id}


@app.route("/cod/status", methods=("GET",))
@login_required
def cod_status():
    """Poll generation progress."""
    session_id = session.get('cod_session_id', '')
    if not session_id:
        return {"status": "idle"}

    progress = ai_get_progress(session_id)

    # If complete, clean up and return the URL
    if progress.get("status") == "complete":
        url = progress.get("url", f"/course/{session_id}")
        ai_clear_progress(session_id)
        session.pop('cod_state', None)
        session.pop('cod_session_id', None)
        return {"status": "complete", "url": url}

    if progress.get("status") == "error":
        ai_clear_progress(session_id)
        return {"status": "error", "error": progress.get("error", "Unknown error")}

    return progress

# Legacy generate_cod_full_content has been replaced by
# ai.pipelines.course_pipeline.generate_course()
# The old function is kept as a thin compatibility wrapper.
def generate_cod_full_content(syllabus):
    backgrounds = get_available_backgrounds()
    return ai_generate_course(syllabus=syllabus, backgrounds=backgrounds)


def normalize_builder_json(blocks):
    """Normalize AI-generated builder blocks to match the builder's expected schema.
    
    The AI might output blocks in either format:
      - New format: {"type": "text", "data": {"text": "..."}}
      - Old/flat format: {"type": "text", "content": "..."}
    This ensures all blocks use the correct {"type": ..., "data": {...}} structure.
    """
    normalized = []
    for block in blocks:
        block_type = block.get('type', 'text')
        
        # If block already has a proper 'data' dict, keep it
        if 'data' in block and isinstance(block['data'], dict):
            normalized.append({"type": block_type, "data": block['data']})
            continue
        
        # Otherwise, convert flat format to data-based format
        if block_type == 'heading':
            normalized.append({"type": "heading", "data": {"text": block.get('content', 'Heading')}})
        elif block_type == 'text':
            normalized.append({"type": "text", "data": {"text": block.get('content', '')}})
        elif block_type == 'code':
            normalized.append({"type": "code", "data": {
                "lang": block.get('lang', 'python'),
                "code": block.get('content', '')
            }})
        elif block_type == 'callout':
            normalized.append({"type": "callout", "data": {
                "type": block.get('variant', block.get('callout_type', 'info')),
                "title": block.get('title', 'Note'),
                "body": block.get('content', block.get('body', ''))
            }})
        elif block_type == 'quiz':
            normalized.append({"type": "quiz", "data": {
                "question": block.get('question', ''),
                "options": block.get('options', ['Option A', 'Option B']),
                "correct": block.get('correct', 0)
            }})
        elif block_type == 'image':
            normalized.append({"type": "image", "data": {"url": block.get('url', block.get('content', ''))}})
        else:
            # Fallback: wrap as text
            normalized.append({"type": "text", "data": {"text": block.get('content', str(block))}})
    
    return normalized


def builder_json_to_html(blocks):
    """Convert builder_json blocks into HTML content (server-side equivalent of
    the lesson builder's generateFinalHtml JS function)."""
    import html as html_module
    
    parts = []
    for blk in blocks:
        btype = blk.get('type', '')
        data = blk.get('data', {})
        
        if btype == 'heading':
            text = data.get('text', '')
            parts.append(f'<h2 class="mb-8 mt-12 text-3xl font-extrabold tracking-tight text-gray-900">{text}</h2>')
        
        elif btype == 'text':
            text = data.get('text', '')
            parts.append(f'<p class="text-lg leading-relaxed text-gray-600 mb-6 font-medium">{text}</p>')
        
        elif btype == 'image':
            url = data.get('url', '')
            if url:
                parts.append(f'<div class="my-12 rounded-2xl overflow-hidden border border-gray-200 shadow-sm"><img src="{html_module.escape(url)}" class="w-full h-auto block"></div>')
        
        elif btype == 'code':
            lang = data.get('lang', 'python')
            code = html_module.escape(data.get('code', ''))
            parts.append(f"""
<div class="relative overflow-hidden rounded-xl border border-gray-800 bg-gray-900 shadow-xl my-10 not-prose group">
    <div class="flex items-center justify-between border-b border-gray-800 bg-black/20 px-5 py-3.5">
        <div class="flex items-center gap-4">
            <div class="flex gap-1.5">
                <div class="h-2.5 w-2.5 rounded-full bg-gray-800"></div>
                <div class="h-2.5 w-2.5 rounded-full bg-gray-800"></div>
                <div class="h-2.5 w-2.5 rounded-full bg-gray-800"></div>
            </div>
            <div class="h-4 w-[1px] bg-gray-800"></div>
            <span class="text-[11px] font-bold uppercase tracking-widest text-gray-500 font-mono">{lang}</span>
        </div>
        <button onclick="copyToClipboard(this)" data-code="{code}" class="flex items-center gap-2 rounded-md bg-gray-800 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider text-gray-400 transition-all hover:bg-gray-700 hover:text-white">
            <i data-lucide="copy" class="w-3.5 h-3.5"></i>
            <span>Copy</span>
        </button>
    </div>
    <div class="p-8 font-mono text-[14px] leading-relaxed text-gray-300 overflow-x-auto whitespace-pre">{code}</div>
</div>""")
        
        elif btype == 'callout':
            callout_type = data.get('type', 'info')
            title = data.get('title', 'Note')
            body = data.get('body', '')
            
            # Extended callout type styling
            callout_styles = {
                'warning':        {'border': 'border-amber-200 bg-amber-50',  'icon': 'alert-triangle',  'color': 'text-amber-600'},
                'common_mistake': {'border': 'border-red-200 bg-red-50',      'icon': 'x-circle',        'color': 'text-red-600'},
                'analogy':        {'border': 'border-violet-200 bg-violet-50','icon': 'lightbulb',       'color': 'text-violet-600'},
                'beginner_tip':   {'border': 'border-emerald-200 bg-emerald-50','icon': 'heart',         'color': 'text-emerald-600'},
                'recap':          {'border': 'border-indigo-200 bg-indigo-50','icon': 'list-checks',     'color': 'text-indigo-600'},
                'expected_output':{'border': 'border-gray-200 bg-gray-50',   'icon': 'terminal',        'color': 'text-gray-600'},
                'info':           {'border': 'border-sky-200 bg-sky-50',     'icon': 'info',            'color': 'text-sky-600'},
            }
            style = callout_styles.get(callout_type, callout_styles['info'])
            
            parts.append(f"""
<div class="my-10 rounded-2xl border {style['border']} p-8 flex gap-6 not-prose shadow-sm">
    <div class="w-14 h-14 shrink-0 rounded-2xl bg-white border border-inherit flex items-center justify-center shadow-sm">
        <i data-lucide="{style['icon']}" class="w-6 h-6 {style['color']}"></i>
    </div>
    <div>
        <h4 class="text-xs font-bold uppercase tracking-widest text-gray-900 mb-2">{title}</h4>
        <div class="text-base font-medium leading-relaxed text-gray-700">{body}</div>
    </div>
</div>""")
        
        elif btype == 'quiz':
            question = data.get('question', '')
            options = data.get('options', [])
            correct = data.get('correct', 0)
            
            options_html = ''
            for i, opt in enumerate(options):
                options_html += f"""
        <button type="button" onclick="checkQuiz(this, {i})" class="group flex items-center justify-between p-5 border border-gray-100 rounded-xl text-left font-bold transition-all hover:border-gray-900 hover:bg-gray-50">
            <span class="text-gray-700">{opt}</span>
            <div class="w-5 h-5 rounded-full border border-gray-200 group-hover:border-gray-900"></div>
        </button>"""
            
            parts.append(f"""
<div class="quiz-container my-12 p-10 rounded-2xl border border-gray-200 bg-white shadow-sm" data-correct="{correct}">
    <div class="flex items-center gap-4 mb-8">
        <div class="w-8 h-8 rounded-xl bg-gray-900 flex items-center justify-center text-xs text-white font-bold">?</div>
        <h3 class="text-xl font-bold tracking-tight text-gray-900">{question}</h3>
    </div>
    <div class="grid gap-3">{options_html}
    </div>
</div>""")
    
    return '\n'.join(parts)


#  Init 

database.init_app(app)

# Auto-ingest educational dataset on startup
try:
    from ai.ingestion import ensure_ingested
    with app.app_context():
        ensure_ingested()
except Exception as e:
    print(f"[STARTUP] Dataset ingestion skipped: {e}")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
