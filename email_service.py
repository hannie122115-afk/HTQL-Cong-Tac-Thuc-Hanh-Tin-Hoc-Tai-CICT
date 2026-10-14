import os
import aiosmtplib

from dotenv import load_dotenv
from email.message import EmailMessage

load_dotenv() #đọc các biến đc khai báo trong .env


async def send_account_email(
    to_email: str,
    username: str,
    setup_link: str,
):
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_email or not smtp_password:
        raise RuntimeError("Chưa cấu hình SMTP_EMAIL hoặc SMTP_PASSWORD.")

    message = EmailMessage()
    message["Subject"] = "Thông tin tài khoản Edu-LIMS"
    message["From"] = smtp_email
    message["To"] = to_email

    message.set_content(
        f"""Xin chào,

Tài khoản Edu-LIMS của bạn đã được tạo.

Tên đăng nhập: {username}

Để thiết lập mật khẩu, vui lòng mở liên kết:
{setup_link}

Nếu bạn không yêu cầu tạo tài khoản này, hãy liên hệ quản trị viên.

Trân trọng,
Edu-LIMS
"""
    )

    await aiosmtplib.send(
        message,
        hostname=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        port=int(os.getenv("SMTP_PORT", "587")),
        username=smtp_email,
        password=smtp_password,
        start_tls=True,
        timeout=30,
    )