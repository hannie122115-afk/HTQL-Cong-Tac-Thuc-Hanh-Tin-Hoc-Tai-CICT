from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from database import get_connection

router = APIRouter()

templates = Jinja2Templates(directory="templates")

@router.get("/admin")
def show_admin(request: Request):
    role = request.session.get("role")

    if role != 0:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(request=request, name="admin/index.html")
