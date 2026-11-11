from typing import Dict, Iterable, Optional, Set

from database import get_connection

NOTIFICATION_TYPE_SCHEDULE = "LICH_THUC_HANH"
NOTIFICATION_TYPE_SCHEDULE_REQUEST = "YEU_CAU_XEP_LICH"
NOTIFICATION_TYPE_STATUS_REPORT = "BAO_CAO_TINH_TRANG"


def insert_notification(
    cursor,
    account_id: int,
    notification_type: str,
    entity_id: Optional[int] = None,
) -> None:
    cursor.execute(
        """
            INSERT INTO THONG_BAO (MaTaiKhoan, LoaiThongBao, MaDoiTuong)
            VALUES (%s, %s, %s)
        """,
        (account_id, notification_type, entity_id),
    )


# ds tk nhan thong bao khi lich doi
def get_schedule_notification_accounts(
    cursor,
    request_ids: Iterable[int],
) -> Dict[int, Set[int]]:
    request_ids = set(request_ids)
    if not request_ids:
        return {}

    cursor.execute(
        """
            SELECT lth.MaLichThucHanh, nd.MaTaiKhoan
            FROM LICH_THUC_HANH lth
            JOIN LOP_HOC_PHAN lhp ON lhp.MaLopHocPhan = lth.MaLopHocPhan
            JOIN NGUOI_DUNG nd ON nd.MaNguoiDung = lhp.MaGiangVien
            WHERE lth.MaLichThucHanh = ANY(%s)
        """,
        (list(request_ids),),
    )
    recipients = {request_id: set() for request_id in request_ids}
    for request_id, teacher_account_id in cursor.fetchall():
        if teacher_account_id is not None:
            recipients[request_id].add(teacher_account_id)
    return recipients


# gui tb
def notify_schedule_recipients(
    cursor,
    request_ids: Iterable[int],
    previous_recipients: Dict[int, Set[int]],
) -> None:
    request_ids = set(request_ids)
    current_recipients = get_schedule_notification_accounts(cursor, request_ids)
    for request_id in request_ids:
        recipients = previous_recipients.get(request_id, set())
        recipients.update(current_recipients.get(request_id, set()))
        for account_id in recipients:
            insert_notification(
                cursor,
                account_id,
                NOTIFICATION_TYPE_SCHEDULE,
                request_id,
            )


def get_unread_notification_types(account_id: int) -> Set[str]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
                SELECT DISTINCT LoaiThongBao
                FROM THONG_BAO
                WHERE MaTaiKhoan = %s AND DaXem = FALSE
            """,
            (account_id,),
        )
        return {row[0] for row in cursor.fetchall()}
    finally:
        conn.close()


def mark_notifications_read(
    account_id: int,
    notification_type: str,
    entity_id: Optional[int] = None,
) -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if entity_id is None:
            cursor.execute(
                """
                    UPDATE THONG_BAO
                    SET DaXem = TRUE
                    WHERE MaTaiKhoan = %s
                      AND LoaiThongBao = %s
                      AND DaXem = FALSE
                """,
                (account_id, notification_type),
            )
        else:
            cursor.execute(
                """
                    UPDATE THONG_BAO
                    SET DaXem = TRUE
                    WHERE MaTaiKhoan = %s
                      AND LoaiThongBao = %s
                      AND MaDoiTuong = %s
                      AND DaXem = FALSE
                """,
                (account_id, notification_type, entity_id),
            )
        conn.commit()
        cursor.close()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
