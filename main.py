# from fastapi import FastAPI, Depends
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles
# from contextlib import asynccontextmanager
# from sqlmodel import Session, select
# import os

# from database import create_db_and_tables, engine
# from api import auth, users, media, categories, dashboard, general_api, media_interactions
# from models.user import User
# from services.auth_service import get_password_hash
# from core.config import settings

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # --- Startup Event ---
#     print("Attempting to connect to the database and create tables...")
#     create_db_and_tables()
#     print("Database initialization complete.")
#     seed_admin()
#     yield
#     # --- Shutdown Event ---
#     print("Application shutdown.")

# app = FastAPI(lifespan=lifespan, title="FastAPI SQLModel Backend")

# @app.on_event("startup")
# def seed_admin():
#     admin_email = settings.ADMIN_EMAIL
#     admin_password = settings.ADMIN_PASSWORD
#     admin_name = settings.ADMIN_NAME

#     with Session(engine) as db:
#         existing_admin = db.exec(select(User).where(User.email == admin_email)).first()
#         if not existing_admin:
#             admin_user = User(
#                 name=admin_name,  # <-- Add this
#                 email=admin_email,
#                 hashed_password=get_password_hash(admin_password),
#                 role="admin"
#             )
#             db.add(admin_user)
#             db.commit()
#             print("✅ Admin user created")
#         else:
#             print("ℹ️ Admin user already exists")

# # CORS (same origins you had)
# # origins = [
# #     "http://localhost:5173",
# #     "http://127.0.0.1:5173",
# # ]


# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=settings.FRONTEND_ORIGINS,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # static mounting (unchanged)
# app.mount("/static", StaticFiles(directory="static"), name="static")

# # include routers (these routers define the same routes you had)
# app.include_router(auth.router)
# app.include_router(users.router)
# app.include_router(media.router)
# app.include_router(categories.router)
# app.include_router(dashboard.router)
# app.include_router(general_api.router)
# app.include_router(media_interactions.router)


# # Root test endpoint (kept)
# @app.get("/")
# def read_root():
#     return {"Hello": "World", "Status": "Backend Running and Connected to DB"}






################################
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from contextlib import asynccontextmanager

from database import engine
from models.user import User
from services.auth_service import get_password_hash
from core.config import settings
import os

from api import auth, users, media, categories, dashboard, general_api, media_interactions, comment_interactions, subscription


def seed_admin():
    """Ensure admin user exists in DB"""
    with Session(engine) as db:
        existing_admin = db.exec(select(User).where(User.email == settings.ADMIN_EMAIL)).first()
        if not existing_admin:
            admin_user = User(
                name=settings.ADMIN_NAME,
                email=settings.ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                role="admin"
            )
            db.add(admin_user)
            db.commit()
            print("✅ Admin user created")
        else:
            print("ℹ️ Admin already exists")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 App starting up...")
    seed_admin()
    yield
    print("🛑 App shutting down...")


app = FastAPI(lifespan=lifespan, title="FastAPI SQLModel Backend")

# CORS
app.add_middleware(
    CORSMiddleware,
    # allow_origins=settings.FRONTEND_ORIGINS,
     allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static", exist_ok=True)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(media.router)
app.include_router(categories.router)
app.include_router(dashboard.router)
app.include_router(general_api.router)
app.include_router(media_interactions.router)
app.include_router(comment_interactions.router)
app.include_router(subscription.router)


@app.get("/")
def read_root():
    return {"message": "Backend running and connected to DB!"}

