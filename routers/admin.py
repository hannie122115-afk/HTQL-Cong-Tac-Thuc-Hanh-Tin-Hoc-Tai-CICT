from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from typing import List

from database import get_connection

router = APIRouter()

templates = Jinja2Templates(directory="templates")


# Trang chu
def get_user_by_id(accountId):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT *
            FROM QUAN_TRI_VIEN
            WHERE MaTaiKhoan = %s
        """,
        (accountId,),
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return user


@router.get("/admin")
def show_admin(request: Request):
    role = request.session.get("role")

    if role != 0:
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    avt = request.session.get("avt")

    return templates.TemplateResponse(
        request=request, name="admin/index.html", context={"user": user, "avt": avt}
    )


# Cau hinh may
def get_config(per_page, offset, keyword):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT *
            FROM CAU_HINH
            WHERE 
                Cpu LIKE %s
                OR Ram LIKE %s
                OR OCung LIKE %s
            LIMIT %s OFFSET %s
        """,
        (
            f"%{keyword}%",
            f"%{keyword}%",
            f"%{keyword}%",
            per_page,
            offset,
        ),
    )

    configs = cursor.fetchall()

    cursor.close()
    conn.close()

    return configs


def get_sum_config(keyword):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT COUNT(MaCauHinh)
            FROM CAU_HINH
            WHERE 
                Cpu LIKE %s
                OR Ram LIKE %s
                OR OCung LIKE %s
        """,
        (
            f"%{keyword}%",
            f"%{keyword}%",
            f"%{keyword}%",
        ),
    )

    config = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return config


def get_all_room():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT *
            FROM PHONG
        """,
    )

    rooms = cursor.fetchall()

    cursor.close()
    conn.close()

    return rooms


@router.get("/admin/config")
def show_admin_config(
    request: Request,
    page: int = 1,
    keyword: str = "",
):
    role = request.session.get("role")
    if role != 0:
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    avt = request.session.get("avt")
    rooms = get_all_room()

    per_page = 5  # moi bang hien 5 dong
    offset = (page - 1) * per_page
    configs = get_config(per_page, offset, keyword)
    amount = get_sum_config(keyword)

    return templates.TemplateResponse(
        request=request,
        name="admin/config.html",
        context={
            "configs": configs,
            "page": page,
            "user": user,
            "avt": avt,
            "amount": amount,
            "per_page": per_page,
            "keyword": keyword,
            "rooms": rooms,
        },
    )


@router.post("/admin/config")
def add_config(
    request: Request,
    cpu: str = Form(""),
    ram: str = Form(""),
    hard_drive: str = Form(""),
    screen_card: str = Form(""),
    rooms: List[int] = Form([]),
):
    role = request.session.get("role")
    if role != 0:
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            INSERT INTO CAU_HINH
            (Cpu, Ram, OCung, CardManHinh)
            VALUES (%s, %s, %s, %s)
            RETURNING MaCauHinh
        """,
        (
            cpu,
            ram,
            hard_drive,
            screen_card,
        ),
    )

    configId = cursor.fetchone()[0]

    if rooms:
        for room in rooms:
            cursor.execute(
                """
                    UPDATE PHONG
                    SET MaCauHinh = %s
                    WHERE MaPhong = %s
                """,
                (
                    configId,
                    room,
                ),
            )

    conn.commit()

    cursor.close()
    conn.close()

    return RedirectResponse(
        url="config",
        status_code=303,
    )
