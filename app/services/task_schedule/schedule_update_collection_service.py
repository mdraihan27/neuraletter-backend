from __future__ import annotations

from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from app.db.session import SessionLocal
from app.models.topic import Topic





scheduler = BackgroundScheduler()


if not scheduler.running:
	scheduler.start()


def get_session_for_job():

	return SessionLocal()


def _topic_job_id(topic_id: str) -> str:
	return f"topic_update_{topic_id}"


def _utc_now_ms() -> int:
	return int(datetime.now(tz=timezone.utc).timestamp() * 1000)


def _ms_to_utc_datetime(ms: int) -> datetime:
	return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)


def schedule_topic_update_at(topic_id: str, run_at_ms: int) -> None:
	"""Schedule a single update cycle for a topic at an absolute UTC time (ms).

	If run_at_ms is in the past, it schedules the job to run ASAP.
	"""
	job_id = _topic_job_id(topic_id)

	now_ms = _utc_now_ms()
	if run_at_ms is None:
		return

	if run_at_ms <= now_ms:
		run_at_ms = now_ms + 5_000

	run_date = _ms_to_utc_datetime(run_at_ms)

	try:
		scheduler.add_job(
			run_topic_update_cycle,
			"date",
			run_date=run_date,
			args=[topic_id],
			id=job_id,
			replace_existing=True,
		)
		print(f"Scheduled topic update for {topic_id} at {run_date.isoformat()} (job_id={job_id})")
	except Exception as e:
		print(f"Failed to schedule topic update for {topic_id}: {e}")


def schedule_updates_from_db() -> None:
	"""Schedule update cycles for all topics based on persisted next_update_time."""
	db = SessionLocal()
	try:
		topics = db.query(Topic).all()
		for topic in topics:
			next_time = getattr(topic, "next_update_time", None)
			if not next_time:
				continue
			schedule_topic_update_at(topic.id, int(next_time))
	finally:
		db.close()


def run_topic_update_cycle(topic_id: str) -> None:
	"""Run one update cycle (collect -> email) then persist + schedule the next cycle."""
	db = get_session_for_job()
	try:
		topic = db.query(Topic).filter(Topic.id == topic_id).first()
		if not topic:
			print(f"Scheduled topic update: topic {topic_id} not found")
			return

		if not topic.description:
			print(f"Scheduled topic update: topic {topic_id} has no description; skipping")
			return

		from app.services.mistral.conversation_service import MistralConversationService

		service = MistralConversationService()
		service.run_serp_topic_enrichment(topic, db)

		freq = getattr(topic, "update_frequency_hours", None) or 24
		next_ms = _utc_now_ms() + int(freq) * 60 * 60 * 1000
		topic.next_update_time = next_ms
		db.add(topic)
		db.commit()

		schedule_topic_update_at(topic.id, next_ms)
	finally:
		db.close()


