📸🎥 Media Management System (FastAPI + Vue.js)

A simple media management system built with FastAPI (backend) and Vue.js (frontend).
This project allows users to upload, manage, and organize media files (images, videos, audio) with categories, authentication, and CRUD APIs.

🚀 Features

User Authentication (Register/Login)

Media Management

Upload media (image, video, audio)

Update media (with file replacement & old file removal)

List all media / Get single media

Delete media (with related file cleanup)

Category Management

Create / Update / Delete categories

Assign media to categories

File Handling with proper static file serving

Database Support with SQLAlchemy & SQLite/PostgreSQL/MySQL (configurable)

Frontend using Vue.js for a modern, responsive UI

🛠️ Tech Stack

Backend:

Python 3.10+

FastAPI

SQLAlchemy

Pydantic

Uvicorn

Alembic (for migrations)

Frontend:

Vue.js 3

Axios (API calls)

TailwindCSS (styling)

Database:

SQLite (default, easy setup)

PostgreSQL / MySQL (production-ready, optional)

⚙️ Backend Setup (FastAPI)
# 1. Clone the repo
git clone https://github.com/yourusername/my-fastapi-vue-app.git
cd my-fastapi-vue-app/backend

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run database migrations
alembic upgrade head

# 5. Start FastAPI server
uvicorn app.main:app --reload


FastAPI will be running at 👉 http://127.0.0.1:8000

API docs available at 👉 http://127.0.0.1:8000/docs

⚙️ Frontend Setup (Vue.js)
# 1. Go to frontend
cd ../frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev


Frontend will be running at 👉 http://localhost:5173

🔑 API Endpoints
Auth

POST /auth/register → Register new user

POST /auth/login → Login and get token

Media

POST /media/ → Upload media

PUT /media/{media_id} → Update media (replace file + update DB)

GET /media/ → List all media

GET /media/{media_id} → Get single media detail

DELETE /media/{media_id} → Delete media (remove DB record + file)

Category

POST /categories/ → Create category

PUT /categories/{category_id} → Update category

DELETE /categories/{category_id} → Delete category

🖼️ Future Improvements

Media search & filtering

Role-based access (Admin/Editor/User)

Cloud file storage (AWS S3, GCP, Azure)

Video thumbnail generation with FFmpeg

📜 License

This project is licensed under the MIT License.

👉 Would you like me to also make a frontend system design breakdown (Dashboard pages, navigation, components) so your Vue.js repo README has similar structure?