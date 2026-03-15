"""
SEO Scheduler
Uses APScheduler. Schedules stored in schedules.json (persistent volume).
Supports: daily, weekly, monthly, and custom cron expressions.
"""

import uuid
import logging
from datetime import datetime
from typing import Optional

import fs_utils as fs

logger = logging.getLogger("scheduler")

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False
    logger.warning("APScheduler not installed — scheduling disabled. Run: pip install apscheduler")


class SEOScheduler:
    def __init__(self):
        self._scheduler = None
        self._schedules: list[dict] = []

    def start(self):
        if not HAS_APSCHEDULER:
            return
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._schedules = fs.read_schedules()
        # Re-register all saved schedules
        for sched in self._schedules:
            if sched.get("enabled", True):
                self._register(sched)
        self._scheduler.start()
        logger.info(f"Scheduler started with {len(self._schedules)} schedules")

    def shutdown(self):
        """Shutdown the scheduler gracefully, waiting for running jobs to complete."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=True)

    def is_running(self) -> bool:
        return bool(self._scheduler and self._scheduler.running)

    def list_schedules(self) -> list:
        """Return all schedules with next_run_time from APScheduler"""
        result = []
        for sched in self._schedules:
            entry = dict(sched)
            if self._scheduler:
                job = self._scheduler.get_job(sched["id"])
                entry["next_run"] = job.next_run_time.isoformat() if job and job.next_run_time else None
                entry["job_active"] = job is not None
            result.append(entry)
        return result

    def get_schedule(self, schedule_id: str) -> Optional[dict]:
        return next((s for s in self._schedules if s["id"] == schedule_id), None)

    def add_schedule(self, config: dict) -> dict:
        """
        config: {
          name, frequency: daily|weekly|monthly|custom,
          cron_expr (for custom), hour, minute, day_of_week, day_of_month,
          task_config: {task, target, audience, domain, notes}
        }
        """
        schedule_id = str(uuid.uuid4())[:8]
        sched = {
            "id":          schedule_id,
            "name":        config.get("name", config.get("task_config", {}).get("task", "Unnamed")),
            "frequency":   config.get("frequency", "weekly"),
            "cron_expr":   config.get("cron_expr", ""),
            "hour":        int(config.get("hour", 9)),
            "minute":      int(config.get("minute", 0)),
            "day_of_week": config.get("day_of_week", "mon"),
            "day_of_month":int(config.get("day_of_month", 1)),
            "task_config": config.get("task_config", {}),
            "enabled":     True,
            "created_at":  datetime.utcnow().isoformat(),
            "last_run":    None,
            "run_count":   0,
        }

        self._schedules.append(sched)
        fs.write_schedules(self._schedules)

        if self._scheduler and sched["enabled"]:
            self._register(sched)

        return sched

    def remove_schedule(self, schedule_id: str):
        self._schedules = [s for s in self._schedules if s["id"] != schedule_id]
        fs.write_schedules(self._schedules)
        if self._scheduler:
            try:
                self._scheduler.remove_job(schedule_id)
            except Exception:
                pass

    def _register(self, sched: dict):
        if not self._scheduler:
            return

        trigger = self._build_trigger(sched)
        if not trigger:
            return

        self._scheduler.add_job(
            func=self._execute_schedule,
            trigger=trigger,
            id=sched["id"],
            args=[sched["id"]],
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info(f"Registered schedule {sched['id']}: {sched['name']}")

    def _build_trigger(self, sched: dict):
        freq = sched.get("frequency", "weekly")
        h    = sched.get("hour", 9)
        m    = sched.get("minute", 0)

        if freq == "custom" and sched.get("cron_expr"):
            parts = sched["cron_expr"].split()
            if len(parts) == 5:
                return CronTrigger(
                    minute=parts[0], hour=parts[1],
                    day=parts[2], month=parts[3], day_of_week=parts[4]
                )

        if freq == "daily":
            return CronTrigger(hour=h, minute=m)

        if freq == "weekly":
            return CronTrigger(day_of_week=sched.get("day_of_week", "mon"), hour=h, minute=m)

        if freq == "monthly":
            return CronTrigger(day=sched.get("day_of_month", 1), hour=h, minute=m)

        if freq == "hourly":
            return IntervalTrigger(hours=1)

        return None

    async def _execute_schedule(self, schedule_id: str):
        sched = self.get_schedule(schedule_id)
        if not sched:
            return

        logger.info(f"Executing schedule {schedule_id}: {sched['name']}")

        import fs_utils as fs2
        from pipeline import Pipeline

        run_id    = fs2.new_run_id()
        task_data = sched["task_config"]
        fs2.init_run(run_id, task_data)

        # Update schedule metadata
        for s in self._schedules:
            if s["id"] == schedule_id:
                s["last_run"]  = datetime.utcnow().isoformat()
                s["run_count"] = s.get("run_count", 0) + 1
                s["last_run_id"] = run_id
        fs2.write_schedules(self._schedules)

        pipeline = Pipeline(
            run_id   = run_id,
            task     = task_data.get("task", ""),
            target   = task_data.get("target", ""),
            audience = task_data.get("audience", ""),
            domain   = task_data.get("domain", ""),
            notes    = task_data.get("notes", ""),
        )
        try:
            pipeline.run()
        except Exception as e:
            logger.error(f"Scheduled pipeline {run_id} failed: {e}")
