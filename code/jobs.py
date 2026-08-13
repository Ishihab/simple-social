import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from utils import delete_orphaned_objects_util

logger = logging.getLogger(__name__)


def register_jobs(scheduler: AsyncIOScheduler):
    scheduler.add_job(
        delete_orphaned_objects_util,
        CronTrigger(hour=0, minute=0),
        id="delete_orphaned_objects",
    )
    logger.info("Registered job: delete_orphaned_objects")
