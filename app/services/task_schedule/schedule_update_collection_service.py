from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from app.db.session import SessionLocal
from app.models.topic import Topic
from app.services.mistral.collect_update_service import collect_updates_for_topic


scheduler = BackgroundScheduler()


def _run_combined_task_for_topic(topic_id: str) -> None:
    print(f"[scheduler] Job triggered for topic_id={topic_id} at {datetime.utcnow().isoformat()}Z")

    db = SessionLocal()
    try:
        print(f"[scheduler] Fetching topic from DB for id={topic_id}")
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            print(f"[scheduler] Topic not found for id={topic_id}")
            return

        # Only process topics that have a non-empty description
        if not topic.description or not str(topic.description).strip():
            print(f"[scheduler] Skipping topic without description id={topic_id}")
            return

        print(f"[scheduler] Running collect_updates_for_topic for topic id={topic_id}")
        collect_updates_for_topic(topic, db)
    except Exception as e:
        print(f"[scheduler] Error running combined_task for topic {topic_id}: {e}")
    finally:
        db.close()


def _schedule_recurring_topic_job(topic: Topic) -> None:
    """Schedule a 24h recurring job for a single topic.

    First run is scheduled to start immediately when the scheduler starts,
    then it repeats every 24 hours.
    """

    # Use local time to align with APScheduler's default timezone and avoid
    # "missed by X hours" messages caused by naive UTC datetimes.
    start_time = datetime.now()
    job_id = f"topic_update_{topic.id}"

    try:
        # Interval trigger: run every 24 hours, first run as soon as possible.
        scheduler.add_job(
            _run_combined_task_for_topic,
            "interval",
            [topic.id],
            hours=24,
            next_run_time=start_time,
            id=job_id,
            replace_existing=True,
        )
        print(f"[scheduler] Scheduled topic id={topic.id} every 24h starting at {start_time}")
    except Exception as e:
        print(f"[scheduler] Failed to schedule topic id={topic.id}: {e}")


def start_topic_update_scheduler() -> None:

    try:
        print("[scheduler] start_topic_update_scheduler() called")
        if getattr(scheduler, "running", False):
            # Already started (e.g. in dev reload scenarios)
            print("[scheduler] Topic update scheduler already running")
            return

        print("[scheduler] Initializing topic update scheduler")

        db = SessionLocal()
        try:
            print("[scheduler] Querying topics from database")
            topics = db.query(Topic).all()
            print(f"[scheduler] Found {len(topics)} topics in database")

            for topic in topics:
                print(f"[scheduler] Inspecting topic id={topic.id}, title={getattr(topic, 'title', None)}")

                if not topic.description or not str(topic.description).strip():
                    print(
                        f"[scheduler] Skipping scheduling for topic without description id={topic.id}"
                    )
                    continue

                _schedule_recurring_topic_job(topic)
        finally:
            db.close()

        scheduler.start()
        print("[scheduler] Topic update scheduler started")
    except Exception as e:
        print(f"[scheduler] Failed to start topic update scheduler: {e}")
