from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from database import get_connection

templates = Jinja2Templates(directory="templates")

router = APIRouter()


@router.get("/staff")
def show_admin(request: Request):
    role = request.session.get("role")

    if role != 2:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(request=request, name="staff/index.html")
