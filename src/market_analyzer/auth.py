"""Firebase authentication dependency for FastAPI."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import firebase_admin.auth

from .db_config import get_db

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Verify Firebase ID token and return the user row (get-or-create).

    Returns a dict with: id, firebase_uid, email, display_name, photo_url, has_resume
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        decoded = firebase_admin.auth.verify_id_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    uid = decoded["uid"]
    email = decoded.get("email")
    name = decoded.get("name")
    picture = decoded.get("picture")

    with get_db() as conn:
        cur = conn.cursor()

        # Try to fetch existing user
        cur.execute(
            "SELECT id, firebase_uid, email, display_name, photo_url, has_resume "
            "FROM users WHERE firebase_uid = %s",
            (uid,),
        )
        row = cur.fetchone()

        if row:
            # Update profile info from token in case it changed
            cur.execute(
                "UPDATE users SET email = %s, display_name = %s, photo_url = %s, "
                "updated_at = NOW() WHERE firebase_uid = %s",
                (email, name, picture, uid),
            )
            conn.commit()
            return {
                "id": row[0],
                "firebase_uid": row[1],
                "email": email,
                "display_name": name,
                "photo_url": picture,
                "has_resume": row[5],
            }

        # Create new user
        cur.execute(
            "INSERT INTO users (firebase_uid, email, display_name, photo_url) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (uid, email, name, picture),
        )
        user_id = cur.fetchone()[0]
        conn.commit()

        return {
            "id": user_id,
            "firebase_uid": uid,
            "email": email,
            "display_name": name,
            "photo_url": picture,
            "has_resume": False,
        }
