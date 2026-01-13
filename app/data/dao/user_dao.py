from app.data import get_db_connection

class UserDAO:
    """用户数据访问对象"""
    
    @staticmethod
    def create_user(username, password_hash, email=None):
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
                    (username, password_hash, email)
                )
                conn.commit()
                return True, "User created successfully"
        except Exception as e:
            # Check for unique constraint violation
            if "UNIQUE constraint failed" in str(e):
                return False, "Username already exists"
            return False, str(e)

    @staticmethod
    def get_user_by_username(username):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
