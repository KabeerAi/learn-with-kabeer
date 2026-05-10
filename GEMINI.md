# Learn with Kabeer - Project Instructions

## Project Overview
"Learn with Kabeer" is a web-based Learning Management System (LMS) built with **Flask**. It provides a platform for delivering educational content through structured courses and lessons.

### Key Features
- **User Authentication:** Sign up, log in, and session management.
- **Course Library:** Browsing and enrollment in available courses.
- **Progress Tracking:** Saves user progress through lessons and calculates completion percentages.
- **Content Management:** Lessons support both HTML and Markdown (with custom syntax highlighting for code blocks).
- **Admin Dashboard:** Interface for creating, updating, and deleting courses and lessons.
- **Architecture:** 
  - `app.py`: Main application logic, routing, and custom template filters.
  - `database.py`: Data layer handling SQLite interactions and schema migrations.
  - `templates/`: Jinja2 templates for frontend rendering.
  - `static/`: Static assets (CSS/JS).

### Technologies
- **Backend:** Python, Flask, Flask-Login
- **Database:** SQLite
- **Frontend:** Jinja2, Vanilla CSS (implied by template structure)
- **Utilities:** Markdown, Werkzeug (security)

---

## Building and Running

### Prerequisites
- Python 3.8+
- `pip`

### Setup Instructions
1.  **Virtual Environment:**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate  # Windows
    # or
    source venv/bin/activate  # Linux/macOS
    ```
2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Database Initialization:**
    The application automatically creates and initializes the SQLite database on startup if it doesn't exist. The database file is located at `instance/learn_with_kabeer.sqlite3`.

### Running the Project
To start the development server:
```bash
python app.py
```
Or using the Flask CLI:
```bash
set FLASK_APP=app.py
set FLASK_DEBUG=1
flask run
```
The application will be available at `http://127.0.0.1:5000`.

---

## Development Conventions

### Data Layer
- **Always** use `database.py` for database operations. Avoid direct `sqlite3` calls in `app.py`.
- The database uses `sqlite3.Row` for dictionary-like access to results.

### Security and Access Control
- Use the `@login_required` decorator for routes that require an authenticated user.
- Use the `@admin_required` decorator for routes that require administrator privileges.
- Password hashing is handled via `werkzeug.security`.

### Content Rendering
- Lessons can be stored as Markdown. Use the `| markdown` filter in Jinja2 templates to render it.
- The Markdown renderer includes custom support for language-specific code blocks (Python, JS, HTML, CSS, Terminal).

### Templates
- All templates should extend `base.html` to maintain a consistent UI.
- Use `flash()` for user notifications (success, error, info).

### Contribution Workflow
1.  **New Features:** Add routes in `app.py` and corresponding data methods in `database.py`.
2.  **Schema Changes:** Update the `init_db()` function in `database.py` to include new tables or columns.
3.  **Testing:** Manually verify changes by running the local server. (TODO: Add automated test suite if project grows).
