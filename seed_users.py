import os
import random
from app import app
import database
from werkzeug.security import generate_password_hash

def seed():
    with app.app_context():
        # Ensure DB is initialized
        database.init_db()

        db = database.get_db()
        
        print("Creating 4 test courses with 10 lessons each...")
        course_ids = []
        for c in range(1, 5):
            slug = f"test-course-{c}"
            # Check if exists
            existing = db.execute("SELECT id FROM courses WHERE slug = ?", (slug,)).fetchone()
            if existing:
                course_id = existing["id"]
            else:
                course_row = database.create_course(slug, f"Test Course {c}", f"Testing Course {c} Description", "Beginner", "active")
                course_id = course_row["id"]
                
                # Create 10 lessons for this course
                for l in range(1, 11):
                    database.create_lesson(
                        course_id=course_id,
                        number=l,
                        slug=f"lesson-{l}",
                        title=f"Lesson {l} for Course {c}",
                        summary=f"This is a test summary for lesson {l}.",
                        content=f"<h1>Lesson {l}</h1><p>Test content for course {c}.</p>",
                        route_name=None,
                        content_type="html"
                    )
            course_ids.append(course_id)

        print("Generating 45 sample users and assigning XP...")
        for i in range(1, 46):
            name = f"Test Player {i}"
            email = f"player{i}@example.com"
            password = generate_password_hash("password123")
            
            try:
                # Fetch if exists from previous runs
                existing_user = database.get_user_by_email(email)
                if existing_user:
                    user_id = existing_user["id"]
                else:
                    user = database.create_user(name, email, password)
                    user_id = user["id"]
                
                # Give them random XP between 50 and 800
                total_xp = random.randint(50, 800)
                
                # We split this into a few activities to simulate real usage
                num_activities = random.randint(1, 5)
                for _ in range(num_activities):
                    activity_xp = total_xp // num_activities
                    if activity_xp > 0:
                        random_course = random.choice(course_ids)
                        # Award XP for simulated activity
                        database.award_xp(user_id, activity_xp, "lesson_complete", course_id=random_course)
                
                print(f"Processed {name} with ~{total_xp} XP.")
            except Exception as e:
                print(f"Failed to process {name}: {e}")
        
        print("Done seeding data!")

if __name__ == "__main__":
    seed()
