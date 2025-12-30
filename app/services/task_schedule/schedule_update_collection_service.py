from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from app.db.session import SessionLocal
from app.models.topic import Topic
from app.services.mistral.collect_update_service import combined_task
import time


scheduler = BackgroundScheduler()


def _run_combined_task_for_topic(topic_id: str) -> None:

    db = SessionLocal()
    try:
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            print(f"[scheduler] Topic not found for id={topic_id}")
            return

        # Only process topics that have a non-empty description
        if not topic.description or not str(topic.description).strip():
            print(f"[scheduler] Skipping topic without description id={topic_id}")
            return

        print(f"[scheduler] Running combined_task for topic id={topic_id}")
        combined_task(topic)
    except Exception as e:
        print(f"[scheduler] Error running combined_task for topic {topic_id}: {e}")
    finally:
        db.close()


def _schedule_recurring_topic_job(topic: Topic, initial_delay_minutes: int) -> None:
    combined_task(topic)

    start_time = datetime.utcnow() + timedelta(minutes=initial_delay_minutes)
    job_id = f"topic_update_{topic.id}"

    try:
        # Interval trigger: run every 24 hours, first run after the given delay.
        scheduler.add_job(
            _run_combined_task_for_topic,
            "interval",
            [topic.id],
            hours=24,
            next_run_time=start_time,
            id=job_id,
            replace_existing=True,
        )
        print(f"[scheduler] Scheduled topic id={topic.id} every 24h starting at {start_time} (delay {initial_delay_minutes} min)")
    except Exception as e:
        print(f"[scheduler] Failed to schedule topic id={topic.id}: {e}")


def start_topic_update_scheduler() -> None:

    try:
        if getattr(scheduler, "running", False):
            # Already started (e.g. in dev reload scenarios)
            print("[scheduler] Topic update scheduler already running")
            return

        print("[scheduler] Initializing topic update scheduler")

        db = SessionLocal()
        try:
            topics = db.query(Topic).all()
            print(f"[scheduler] Found {len(topics)} topics in database")

            # Space out initial runs by 5 minutes between topics
            offset_minutes = 0
            for topic in topics:
                if not topic.description or not str(topic.description).strip():
                    print(f"[scheduler] Skipping scheduling for topic without description id={topic.id}")
                    continue

                _schedule_recurring_topic_job(topic, offset_minutes)
                # offset_minutes += 5
                time.sleep(5 * 60)
        finally:
            db.close()

        scheduler.start()
        print("[scheduler] Topic update scheduler started")
    except Exception as e:
        print(f"[scheduler] Failed to start topic update scheduler: {e}")
