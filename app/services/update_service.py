from typing import List

from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.models.topic import Topic
from app.models.update import Update


class UpdateService:

	def get_updates_for_topic(self, topic_id: str, authenticated_user_id: str, db: Session) -> JSONResponse:
		"""Fetch all updates for a topic, ensuring the topic belongs to the user."""
		try:
			topic = (
				db.query(Topic)
				.filter(Topic.id == topic_id, Topic.associated_user_id == authenticated_user_id)
				.first()
			)

			if not topic:
				return JSONResponse(
					content={"message": "Topic not found"},
					status_code=404,
				)

			updates: List[Update] = (
				db.query(Update)
				.filter(Update.associated_topic_id == topic_id)
				.order_by(Update.created_at.desc())
				.all()
			)

			updates_list = []
			for update in updates:
				# key_points are stored as JSON array string in DB; best-effort parse
				key_points_value = []
				if update.key_points:
					try:
						import json

						parsed = json.loads(update.key_points)
						if isinstance(parsed, list):
							key_points_value = parsed
					except Exception:
						# On any parsing error, just fall back to empty list
						key_points_value = []

				updates_list.append(
					{
						"id": update.id,
						"title": update.title,
						"author": update.author,
						"date": update.date,
						"key_points": key_points_value,
						"image_link": update.image_link,
						"created_at": update.created_at,
					}
				)

			return JSONResponse(
				content={
					"message": "Updates fetched successfully",
					"updates": updates_list,
				},
				status_code=200,
			)
		except Exception as e:
			print(f"Failed to fetch updates: {e}")
			return JSONResponse(
				content={"message": "Failed to fetch updates"},
				status_code=500,
			)

