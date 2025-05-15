"""Limitless scheduler service for InkLink.

This module provides a scheduler service for regular Limitless Life Log syncing.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from inklink.services.limitless_life_log_service import LimitlessLifeLogService

logger = logging.getLogger(__name__)


class LimitlessSchedulerService:
    """
    Scheduler service for regular Limitless Life Log syncing.

    This service runs a background thread to periodically sync life logs
    based on a configurable interval.
    """

    def __init__(
        self,
        limitless_service: LimitlessLifeLogService,
        sync_interval: int = 3600,  # Default to hourly syncing
        initial_delay: int = 60,  # Wait 60 seconds before first sync
    ):
        """
        Initialize the scheduler service.

        Args:
            limitless_service: Limitless Life Log service to use for syncing
            sync_interval: Interval between syncs in seconds
            initial_delay: Delay in seconds before first sync
        """
        self.limitless_service = limitless_service
        self.sync_interval = sync_interval
        self.initial_delay = initial_delay
        self.thread = None
        self.running = False
        self.last_sync_time = None
        self.next_sync_time = None
        self.sync_status = "idle"

    def start(self):
        """
        Start the scheduler background thread.

        Returns:
            True if started, False if already running
        """
        if self.running:
            logger.warning("Scheduler already running")
            return False

        self.running = True
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()

        logger.info(
            f"Limitless scheduler started with interval {self.sync_interval}s "
            f"and initial delay {self.initial_delay}s"
        )
        return True

    def stop(self):
        """
        Stop the scheduler background thread.

        Returns:
            True if stopped, False if not running
        """
        if not self.running:
            logger.warning("Scheduler not running")
            return False

        logger.info("Stopping Limitless scheduler")
        self.running = False

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)

        return True

    def _scheduler_loop(self):
        """
        Main scheduler loop that runs in the background thread.
        """
        # Wait for initial delay
        if self.initial_delay > 0:
            logger.info(f"Waiting {self.initial_delay}s before first sync")
            time.sleep(self.initial_delay)

        while self.running:
            try:
                # Update status
                self.sync_status = "syncing"
                logger.info("Starting scheduled Limitless Life Log sync")

                # Perform sync
                success, message = self.limitless_service.sync_life_logs()

                # Update status
                self.last_sync_time = datetime.now()
                self.next_sync_time = self.last_sync_time + timedelta(
                    seconds=self.sync_interval
                )
                self.sync_status = "idle"

                if success:
                    logger.info(f"Scheduled sync completed: {message}")
                else:
                    logger.error(f"Scheduled sync failed: {message}")

                # Wait for next sync interval
                wait_time = self.sync_interval
                logger.info(f"Next sync scheduled for {self.next_sync_time}")

                # Sleep in smaller increments to allow for clean shutdown
                sleep_increment = 5  # Check for shutdown every 5 seconds
                for _ in range(int(wait_time / sleep_increment)):
                    if not self.running:
                        break
                    time.sleep(sleep_increment)

                # Sleep any remaining time
                remaining_time = wait_time % sleep_increment
                if remaining_time > 0 and self.running:
                    time.sleep(remaining_time)

            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                self.sync_status = "error"

                # Sleep for a shorter interval after error
                recovery_wait = min(self.sync_interval, 300)  # 5 minutes or less
                time.sleep(recovery_wait)

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current scheduler status.

        Returns:
            Dictionary with scheduler status information
        """
        return {
            "running": self.running,
            "sync_status": self.sync_status,
            "last_sync_time": (
                self.last_sync_time.isoformat() if self.last_sync_time else None
            ),
            "next_sync_time": (
                self.next_sync_time.isoformat() if self.next_sync_time else None
            ),
            "sync_interval": self.sync_interval,
            "service_status": self.limitless_service.get_sync_status(),
        }

    def trigger_sync(self, force_full_sync: bool = False) -> Dict[str, Any]:
        """
        Trigger an immediate sync.

        Args:
            force_full_sync: If True, sync all life logs regardless of last sync time

        Returns:
            Dictionary with sync result information
        """
        logger.info(f"Manual sync triggered (force_full_sync={force_full_sync})")

        # Update status
        self.sync_status = "syncing"

        try:
            # Perform sync
            success, message = self.limitless_service.sync_life_logs(
                force_full_sync=force_full_sync
            )

            # Update status
            self.last_sync_time = datetime.now()
            self.next_sync_time = self.last_sync_time + timedelta(
                seconds=self.sync_interval
            )
            self.sync_status = "idle"

            return {
                "success": success,
                "message": message,
                "timestamp": self.last_sync_time.isoformat(),
                "next_sync": self.next_sync_time.isoformat(),
            }

        except Exception as e:
            error_message = f"Error in manual sync: {str(e)}"
            logger.error(error_message)
            self.sync_status = "error"

            return {
                "success": False,
                "message": error_message,
                "timestamp": datetime.now().isoformat(),
            }
