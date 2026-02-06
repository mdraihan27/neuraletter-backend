from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.utils.user_util import create_user_response
from app.db.session import get_db
from app.models.user import User


def get_user_by_id(user_id: str, db: Session) -> JSONResponse:

    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return JSONResponse(
                content={"message": "User not found"},
                status_code=404
            )

        user_dict = vars(user).copy()
        user_dict.pop("hashed_password", None)
        user_dict.pop("_sa_instance_state", None)  # ✅ FIX

        return JSONResponse(
            content={
                "message": "User fetched successfully",
                "user_info": user_dict
            },
            status_code=200
        )

    except Exception as e:
        print(e)
        return JSONResponse(
            content={"message": "Failed to fetch user"},
            status_code=500
        )


def update_user_info(new_user_info: User, current_user: dict, db: Session) -> JSONResponse:
    try:
        user = db.query(User).filter(User.id == current_user["user_id"]).first()

        if not user:
            return JSONResponse(
                content={"message": "User not found"},
                status_code=404
            )

        if new_user_info.first_name is not None:
            user.first_name = new_user_info.first_name
        if new_user_info.last_name is not None:
            user.first_name = new_user_info.last_name

        db.add(user)
        db.commit()
        db.refresh(user)

        user_response = create_user_response(user)

        return JSONResponse(
            content={
                "message": "User info updated successfully",
                "user": user_response
            },
            status_code=200
        )

    except Exception as e:
        db.rollback()
        print(e)
        return JSONResponse(
            content={"message": "Failed to update user info"},
            status_code=500
        )


def delete_user_account(current_user: dict, db: Session) -> JSONResponse:
    try:
        user = db.query(User).filter(User.id == current_user["user_id"]).first()

        if not user:
            return JSONResponse(
                content={"message": "User not found"},
                status_code=404
            )

        db.delete(user)
        db.commit()

        return JSONResponse(
            content={"message": "User account deleted successfully"},
            status_code=200
        )

    except Exception as e:
        db.rollback()
        print(e)
        return JSONResponse(
            content={"message": "Failed to delete user account"},
            status_code=500
        )