from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from database import get_connection

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login")
def show_login(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")


@router.post("/login")
def login(request: Request, username: str = Form(""), password: str = Form("")):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT MaTaiKhoan, TenTaiKhoan, MatKhau, VaiTro
        FROM TAI_KHOAN_DANG_NHAP
        WHERE TenTaiKhoan = %s
    """,
        (username,),
    )

    account = cursor.fetchone()

    cursor.close()
    conn.close()

    if username == "" or password == "":
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"message": "Vui lòng nhập đầy đủ thông tin!"},
        )

    if account is None:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"message": "Tên đăng nhập không tồn tại!"},
        )
    if account[2] != password:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"message": "Mật khẩu không chính xác!"},
        )

    request.session["accountId"] = account[0]
    request.session["username"] = account[1]
    request.session["role"] = account[3]

    role = account[3]
    if role == 0:
        return RedirectResponse(url="/admin", status_code=303)
    if role == 1:
        return RedirectResponse(url="/teacher", status_code=303)
    if role == 2:
        return RedirectResponse(url="/staff", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
