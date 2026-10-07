from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from database import get_connection

templates = Jinja2Templates(directory="templates")

router = APIRouter()

def get_user_by_id(accountId):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT *
            FROM GIANG_VIEN
            WHERE MaTaiKhoan = %s
        """,
        (accountId,),
    )

    user = cursor.fetchone

    cursor.close()
    conn.close()

    return user


@router.get("/teacher")
def show_admin(request: Request):
    role = request.session.get("role")

    if role != 1:
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    avt = request.session.get("avt")

    return templates.TemplateResponse(
        request=request, name="teacher/index.html", context={"user": user, "avt": avt}
    )
