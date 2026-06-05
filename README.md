# Learn with Kabeer 🚀

Learn with Kabeer is a Learning to Code Platform designed for Programming/Coding education much more easier. It features a premium, tactile UI and uses AI to help synthesize courses and lessons.

## ✨ Features

- **Personal Dashboard:** Track your progress across multiple courses.
- **Interactive Map:** Navigate your learning journey through a beautiful 3D-styled course map.
- **AI-Powered Lessons:** Dynamically generate lessons and curriculum content.
- **Lesson Builder:** A powerful admin tool to design lessons with rich components (Code, Quiz, Callouts, etc.).
- **XP System:** Earn experience points as you complete lessons.
- **Course on Demand (COD):** Synthesize new courses with AI directly from the chat interface.

## 🛠️ Tech Stack

- **Backend:** Python (Flask)
- **Frontend:** Jinja2, Tailwind CSS, Vanilla JS
- **Database:** SQLite
- **Vector Store:** ChromaDB (for AI retrieval)
- **Icons:** Lucide Icons

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### 2. Installation
Clone the repository and set up a virtual environment:
```bash
git clone https://github.com/your-username/learn-with-kabeer.git
cd learn-with-kabeer

# Create virtual environment
python -m venv venv

# Activate on Windows:
.\venv\Scripts\activate
# Activate on macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Dataset Setup 📊
The project requires a specific dataset to function correctly. This dataset is hosted on Kaggle.

1.  **Download:** Go to the [Coding Courses Dataset on Kaggle](https://www.kaggle.com/datasets/ranakabeerali/coding-courses-dataset) and download the files.
2.  **Placement:** Extract the files and place the `dataset` folder in the root directory of this project.
    - Your folder structure should look like: `learn-with-kabeer/dataset/...`
3.  **Ingestion:** Run the ingestion script to prepare the AI vector store:
    ```bash
    python scripts/ingest_dataset.py
    ```

### 4. Running the App
Start the development server:
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:5000`.

---

## 👨‍💻 Admin Access
To access management features:
1.  Register a new account.
2.  Manually set the `is_admin` column to `1` in the `users` table of `instance/learn_with_kabeer.sqlite3` using a database tool (like DB Browser for SQLite).

## 📄 License
This project is for **personal and educational use only**. Commercial use is strictly prohibited. See the [LICENSE](LICENSE) file for more details.
