from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from database import get_connection
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from routers.auth import router as auth_router
from routers.admin import router as admin_router
from routers.staff import router as staff_router
from routers.teacher import router as teacher_router
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(SessionMiddleware, secret_key="122115")
templates = Jinja2Templates(directory="templates")

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(staff_router)
app.include_router(teacher_router)


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")
