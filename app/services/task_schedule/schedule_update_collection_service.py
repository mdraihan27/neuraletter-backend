from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from app.db.session import SessionLocal
from app.models.topic import Topic





scheduler = BackgroundScheduler()


if not scheduler.running:
	scheduler.start()


def get_session_for_job():

	return SessionLocal()


