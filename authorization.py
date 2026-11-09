from database import get_connection


def has_permission(request, permission_name: str) -> bool:
    role_id = request.session.get("role")
    if role_id is None:
        return False

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM vai_tro_quyen vtp
                    JOIN quyen q ON q.maquyen = vtp.maquyen
                    WHERE vtp.mavaitro = %s
                      AND q.tenquyen = %s
                )
                """,
                (role_id, permission_name),
            )
            return cursor.fetchone()[0]
    finally:
        conn.close()
