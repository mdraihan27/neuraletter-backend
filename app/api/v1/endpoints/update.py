from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import JSONResponse

from app.core.auth import get_current_user
from app.db.session import get_db
from app.services.update_service import UpdateService


update_service = UpdateService()

router = APIRouter()


@router.get("/{topic_id}")
def get_updates_by_topic_id(
	topic_id: str,
	current_user: dict = Depends(get_current_user),
	db: Session = Depends(get_db),
):
	try:
		return update_service.get_updates_for_topic(topic_id, current_user["user_id"], db)
	except Exception as e:
		return JSONResponse(
			content={"message": str(e)},
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
		)

