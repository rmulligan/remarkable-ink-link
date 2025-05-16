#!/usr/bin/env python3
"""
Proton Calendar Adapter for Lilly

This adapter provides an interface to access and interact with Proton Calendar
through the CalDAV protocol via Proton Bridge.
"""

import datetime
import logging
import os
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import caldav
from caldav.elements import dav

logger = logging.getLogger(__name__)


@dataclass
class CalendarEvent:
    """Calendar event data structure."""

    uid: str
    summary: str
    description: Optional[str]
    start: datetime.datetime
    end: datetime.datetime
    location: Optional[str] = None
    url: Optional[str] = None
    categories: List[str] = None
    attendees: List[Dict[str, str]] = None
    organizer: Optional[Dict[str, str]] = None
    status: Optional[str] = None
    created: Optional[datetime.datetime] = None
    last_modified: Optional[datetime.datetime] = None
    calendar_id: Optional[str] = None
    recurrence_rule: Optional[str] = None
    all_day: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CalendarEvent":
        """Create a CalendarEvent from a dictionary."""
        # Handle date conversion
        start = data.get("start")
        if isinstance(start, str):
            start = datetime.datetime.fromisoformat(start)

        end = data.get("end")
        if isinstance(end, str):
            end = datetime.datetime.fromisoformat(end)

        created = data.get("created")
        if isinstance(created, str):
            created = datetime.datetime.fromisoformat(created)

        last_modified = data.get("last_modified")
        if isinstance(last_modified, str):
            last_modified = datetime.datetime.fromisoformat(last_modified)

        return cls(
            uid=data.get("uid", str(uuid.uuid4())),
            summary=data.get("summary", ""),
            description=data.get("description"),
            start=start,
            end=end,
            location=data.get("location"),
            url=data.get("url"),
            categories=data.get("categories", []),
            attendees=data.get("attendees", []),
            organizer=data.get("organizer"),
            status=data.get("status"),
            created=created,
            last_modified=last_modified,
            calendar_id=data.get("calendar_id"),
            recurrence_rule=data.get("recurrence_rule"),
            all_day=data.get("all_day", False),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "uid": self.uid,
            "summary": self.summary,
            "description": self.description,
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None,
            "location": self.location,
            "url": self.url,
            "categories": self.categories,
            "attendees": self.attendees,
            "organizer": self.organizer,
            "status": self.status,
            "created": self.created.isoformat() if self.created else None,
            "last_modified": (
                self.last_modified.isoformat() if self.last_modified else None
            ),
            "calendar_id": self.calendar_id,
            "recurrence_rule": self.recurrence_rule,
            "all_day": self.all_day,
        }

    def __str__(self) -> str:
        """String representation of event."""
        return f"{self.summary} ({self.start.strftime('%Y-%m-%d %H:%M')} - {self.end.strftime('%Y-%m-%d %H:%M')})"


class ProtonCalendarAdapter:
    """
    Adapter for interacting with Proton Calendar via CalDAV.

    This adapter uses the CalDAV protocol to communicate with Proton Calendar
    through the Proton Bridge service, which must be installed and configured.
    """

    def __init__(
        self,
        username: str = None,
        password: str = None,
        caldav_url: str = "http://127.0.0.1:8080/",
        cache_dir: Optional[str] = None,
    ):
        """
        Initialize the Proton Calendar adapter.

        Args:
            username: CalDAV username (default: from PROTON_CALENDAR_USERNAME env var)
            password: CalDAV password (default: from PROTON_CALENDAR_PASSWORD env var)
            caldav_url: CalDAV server URL (default: localhost for Proton Bridge)
            cache_dir: Directory to cache calendar data
        """
        # Get credentials from environment variables if not provided
        self.username = username or os.environ.get("PROTON_CALENDAR_USERNAME")
        self.password = password or os.environ.get("PROTON_CALENDAR_PASSWORD")

        if not self.username or not self.password:
            logger.warning(
                "Proton Calendar credentials not provided. Some functionality may be limited."
            )

        # Configure connection settings
        self.caldav_url = caldav_url

        # Caching settings
        self.cache_dir = cache_dir
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)

        # Initialize client as None (lazy initialization)
        self.client = None
        self.principal = None
        self._calendars = None

        logger.info(f"Initialized ProtonCalendarAdapter for {self.username}")

    def _connect(self) -> bool:
        """
        Connect to the CalDAV server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Create CalDAV client
            self.client = caldav.DAVClient(
                url=self.caldav_url, username=self.username, password=self.password
            )

            # Get principal
            self.principal = self.client.principal()

            logger.info(f"Successfully connected to CalDAV server for {self.username}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to CalDAV server: {str(e)}")
            self.client = None
            self.principal = None
            return False

    def _ensure_connected(self) -> bool:
        """
        Ensure connection to CalDAV server is established.

        Returns:
            True if connected, False otherwise
        """
        if self.client is None or self.principal is None:
            return self._connect()

        try:
            # Test connection by getting calendars
            _ = self.principal.calendars()
            return True
        except Exception:
            logger.info("CalDAV connection lost. Reconnecting...")
            return self._connect()

    def get_calendars(
        self, refresh: bool = False
    ) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """
        Get all available calendars.

        Args:
            refresh: Whether to refresh the cached calendar list

        Returns:
            Tuple of (success, calendars/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to CalDAV server"

        try:
            # Get calendars from server
            if self._calendars is None or refresh:
                caldav_calendars = self.principal.calendars()
                self._calendars = []

                for cal in caldav_calendars:
                    try:
                        props = cal.get_properties([dav.DisplayName()])
                        display_name = props.get("{DAV:}displayname", cal.name)

                        self._calendars.append(
                            {
                                "id": cal.name,
                                "url": cal.url,
                                "display_name": display_name,
                            }
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to get properties for calendar {cal.name}: {str(e)}"
                        )

            return True, self._calendars
        except Exception as e:
            logger.error(f"Error getting calendars: {str(e)}")
            return False, f"Error getting calendars: {str(e)}"

    def get_calendar_by_id(
        self, calendar_id: str
    ) -> Tuple[bool, Union[caldav.Calendar, str]]:
        """
        Get a calendar by its ID.

        Args:
            calendar_id: Calendar ID

        Returns:
            Tuple of (success, calendar/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to CalDAV server"

        try:
            # Get all calendars
            status, calendars = self.get_calendars()
            if not status:
                return False, calendars

            # Find the calendar with the given ID
            for cal_info in calendars:
                if cal_info["id"] == calendar_id:
                    calendar = self.client.calendar(url=cal_info["url"])
                    return True, calendar

            return False, f"Calendar with ID {calendar_id} not found"
        except Exception as e:
            logger.error(f"Error getting calendar {calendar_id}: {str(e)}")
            return False, f"Error getting calendar {calendar_id}: {str(e)}"

    def get_events(
        self,
        calendar_id: str,
        start_date: Optional[datetime.datetime] = None,
        end_date: Optional[datetime.datetime] = None,
    ) -> Tuple[bool, Union[List[CalendarEvent], str]]:
        """
        Get events from a calendar.

        Args:
            calendar_id: Calendar ID
            start_date: Start date/time for events (default: today)
            end_date: End date/time for events (default: one month from start)

        Returns:
            Tuple of (success, events/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to CalDAV server"

        try:
            # Get the calendar
            status, calendar = self.get_calendar_by_id(calendar_id)
            if not status:
                return False, calendar

            # Set default date range if not provided
            if start_date is None:
                start_date = datetime.datetime.now().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )

            if end_date is None:
                end_date = start_date + datetime.timedelta(days=30)

            # Get events in the date range
            caldav_events = calendar.date_search(start=start_date, end=end_date)

            # Convert to our event model
            events = []
            for caldav_event in caldav_events:
                event = self._parse_caldav_event(caldav_event, calendar_id)
                if event:
                    events.append(event)

            return True, events
        except Exception as e:
            logger.error(f"Error getting events from calendar {calendar_id}: {str(e)}")
            return False, f"Error getting events from calendar {calendar_id}: {str(e)}"

    def _parse_caldav_event(
        self, caldav_event: caldav.Event, calendar_id: str
    ) -> Optional[CalendarEvent]:
        """
        Parse a CalDAV event into our model.

        Args:
            caldav_event: CalDAV event
            calendar_id: ID of the calendar containing the event

        Returns:
            Parsed CalendarEvent, or None if parsing failed
        """
        try:
            # Get event data
            event_data = caldav_event.data

            # Parse using vobject
            import vobject

            vevent = vobject.readOne(event_data).vevent

            # Extract basic information
            uid = str(getattr(vevent, "uid", str(uuid.uuid4())))
            summary = str(getattr(vevent, "summary", ""))
            description = (
                str(getattr(vevent, "description", ""))
                if hasattr(vevent, "description")
                else None
            )
            location = (
                str(getattr(vevent, "location", ""))
                if hasattr(vevent, "location")
                else None
            )

            # Handle start and end dates
            start = vevent.dtstart.value
            all_day = False

            # Convert to datetime if date
            if isinstance(start, datetime.date) and not isinstance(
                start, datetime.datetime
            ):
                start = datetime.datetime.combine(start, datetime.time.min)
                all_day = True

            # Get end date/time
            if hasattr(vevent, "dtend"):
                end = vevent.dtend.value
                if isinstance(end, datetime.date) and not isinstance(
                    end, datetime.datetime
                ):
                    end = datetime.datetime.combine(end, datetime.time.min)
            else:
                # Default to 1 hour duration
                end = start + datetime.timedelta(hours=1)

            # Get created and last modified
            created = getattr(vevent, "created", None)
            created = created.value if created else None

            last_modified = getattr(vevent, "last_modified", None)
            last_modified = last_modified.value if last_modified else None

            # Get status
            status = (
                str(getattr(vevent, "status", "")).lower()
                if hasattr(vevent, "status")
                else None
            )

            # Get recurrence rule
            rrule = getattr(vevent, "rrule", None)
            recurrence_rule = str(rrule.value) if rrule else None

            # Get URL
            url = str(getattr(vevent, "url", "")) if hasattr(vevent, "url") else None

            # Get categories
            categories = []
            if hasattr(vevent, "categories"):
                categories = vevent.categories.value

            # Get attendees
            attendees = []
            if hasattr(vevent, "attendee_list"):
                for attendee in vevent.attendee_list:
                    cn = attendee.params.get("CN", [""])[0]
                    email = attendee.value.split(":")[-1]
                    role = attendee.params.get("ROLE", ["REQ-PARTICIPANT"])[0]
                    attendees.append({"name": cn, "email": email, "role": role})

            # Get organizer
            organizer = None
            if hasattr(vevent, "organizer"):
                org = vevent.organizer
                cn = org.params.get("CN", [""])[0]
                email = org.value.split(":")[-1]
                organizer = {"name": cn, "email": email}

            # Create event object
            return CalendarEvent(
                uid=uid,
                summary=summary,
                description=description,
                start=start,
                end=end,
                location=location,
                url=url,
                categories=categories,
                attendees=attendees,
                organizer=organizer,
                status=status,
                created=created,
                last_modified=last_modified,
                calendar_id=calendar_id,
                recurrence_rule=recurrence_rule,
                all_day=all_day,
            )
        except Exception as e:
            logger.error(f"Error parsing CalDAV event: {str(e)}")
            return None

    def get_event_by_uid(
        self, calendar_id: str, event_uid: str
    ) -> Tuple[bool, Union[CalendarEvent, str]]:
        """
        Get a specific event by UID.

        Args:
            calendar_id: Calendar ID
            event_uid: Event UID

        Returns:
            Tuple of (success, event/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to CalDAV server"

        try:
            # Get the calendar
            status, calendar = self.get_calendar_by_id(calendar_id)
            if not status:
                return False, calendar

            # Get the event by UID
            try:
                caldav_event = calendar.event_by_uid(event_uid)
                event = self._parse_caldav_event(caldav_event, calendar_id)
                if event:
                    return True, event
                else:
                    return False, f"Failed to parse event {event_uid}"
            except caldav.error.NotFoundError:
                return False, f"Event {event_uid} not found in calendar {calendar_id}"
        except Exception as e:
            logger.error(
                f"Error getting event {event_uid} from calendar {calendar_id}: {str(e)}"
            )
            return False, f"Error getting event {event_uid}: {str(e)}"

    def create_event(
        self, calendar_id: str, event: CalendarEvent
    ) -> Tuple[bool, Union[str, CalendarEvent]]:
        """
        Create a new event in a calendar.

        Args:
            calendar_id: Calendar ID
            event: Event data

        Returns:
            Tuple of (success, created_event/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to CalDAV server"

        try:
            # Get the calendar
            status, calendar = self.get_calendar_by_id(calendar_id)
            if not status:
                return False, calendar

            # Create the event
            import vobject

            ical = vobject.iCalendar()
            vevent = ical.add("vevent")

            # Set properties
            vevent.add("uid").value = event.uid
            vevent.add("summary").value = event.summary

            if event.description:
                vevent.add("description").value = event.description

            # Set start and end
            if event.all_day:
                # All-day event
                vevent.add("dtstart").value = event.start.date()
                vevent.add("dtend").value = event.end.date()
            else:
                # Timed event
                vevent.add("dtstart").value = event.start
                vevent.add("dtend").value = event.end

            # Add other properties
            if event.location:
                vevent.add("location").value = event.location

            if event.url:
                vevent.add("url").value = event.url

            if event.status:
                vevent.add("status").value = event.status

            if event.recurrence_rule:
                vevent.add("rrule").value = event.recurrence_rule

            if event.categories:
                cats = vevent.add("categories")
                cats.value = event.categories

            # Add attendees
            if event.attendees:
                for attendee in event.attendees:
                    a = vevent.add("attendee")
                    a.value = f"mailto:{attendee.get('email', '')}"
                    if attendee.get("name"):
                        a.params["CN"] = [attendee["name"]]
                    if attendee.get("role"):
                        a.params["ROLE"] = [attendee["role"]]

            # Add organizer
            if event.organizer:
                o = vevent.add("organizer")
                o.value = f"mailto:{event.organizer.get('email', '')}"
                if event.organizer.get("name"):
                    o.params["CN"] = [event.organizer["name"]]

            # Add timestamps
            now = datetime.datetime.now()
            vevent.add("dtstamp").value = now
            vevent.add("created").value = now
            vevent.add("last-modified").value = now

            # Create the event on the server
            caldav_event = calendar.save_event(ical.serialize())

            # Get the created event
            created_event = self._parse_caldav_event(caldav_event, calendar_id)

            return True, created_event

        except Exception as e:
            logger.error(f"Error creating event in calendar {calendar_id}: {str(e)}")
            return False, f"Error creating event: {str(e)}"

    def update_event(
        self, calendar_id: str, event: CalendarEvent
    ) -> Tuple[bool, Union[str, CalendarEvent]]:
        """
        Update an existing event.

        Args:
            calendar_id: Calendar ID
            event: Updated event data (must have a valid UID)

        Returns:
            Tuple of (success, updated_event/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to CalDAV server"

        try:
            # Get the calendar
            status, calendar = self.get_calendar_by_id(calendar_id)
            if not status:
                return False, calendar

            # Get the existing event
            try:
                caldav_event = calendar.event_by_uid(event.uid)
            except caldav.error.NotFoundError:
                return False, f"Event {event.uid} not found in calendar {calendar_id}"

            # Create updated iCalendar data
            import vobject

            ical = vobject.iCalendar()
            vevent = ical.add("vevent")

            # Set properties
            vevent.add("uid").value = event.uid
            vevent.add("summary").value = event.summary

            if event.description:
                vevent.add("description").value = event.description

            # Set start and end
            if event.all_day:
                # All-day event
                vevent.add("dtstart").value = event.start.date()
                vevent.add("dtend").value = event.end.date()
            else:
                # Timed event
                vevent.add("dtstart").value = event.start
                vevent.add("dtend").value = event.end

            # Add other properties
            if event.location:
                vevent.add("location").value = event.location

            if event.url:
                vevent.add("url").value = event.url

            if event.status:
                vevent.add("status").value = event.status

            if event.recurrence_rule:
                vevent.add("rrule").value = event.recurrence_rule

            if event.categories:
                cats = vevent.add("categories")
                cats.value = event.categories

            # Add attendees
            if event.attendees:
                for attendee in event.attendees:
                    a = vevent.add("attendee")
                    a.value = f"mailto:{attendee.get('email', '')}"
                    if attendee.get("name"):
                        a.params["CN"] = [attendee["name"]]
                    if attendee.get("role"):
                        a.params["ROLE"] = [attendee["role"]]

            # Add organizer
            if event.organizer:
                o = vevent.add("organizer")
                o.value = f"mailto:{event.organizer.get('email', '')}"
                if event.organizer.get("name"):
                    o.params["CN"] = [event.organizer["name"]]

            # Add timestamps
            now = datetime.datetime.now()
            vevent.add("dtstamp").value = now
            if event.created:
                vevent.add("created").value = event.created
            else:
                vevent.add("created").value = now
            vevent.add("last-modified").value = now

            # Update the event on the server
            caldav_event.data = ical.serialize()
            caldav_event.save()

            # Get the updated event
            updated_event = self._parse_caldav_event(caldav_event, calendar_id)

            return True, updated_event

        except Exception as e:
            logger.error(
                f"Error updating event {event.uid} in calendar {calendar_id}: {str(e)}"
            )
            return False, f"Error updating event: {str(e)}"

    def delete_event(self, calendar_id: str, event_uid: str) -> Tuple[bool, str]:
        """
        Delete an event.

        Args:
            calendar_id: Calendar ID
            event_uid: Event UID

        Returns:
            Tuple of (success, message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to CalDAV server"

        try:
            # Get the calendar
            status, calendar = self.get_calendar_by_id(calendar_id)
            if not status:
                return False, calendar

            # Get the event
            try:
                caldav_event = calendar.event_by_uid(event_uid)
            except caldav.error.NotFoundError:
                return False, f"Event {event_uid} not found in calendar {calendar_id}"

            # Delete the event
            caldav_event.delete()

            return True, f"Event {event_uid} deleted from calendar {calendar_id}"
        except Exception as e:
            logger.error(
                f"Error deleting event {event_uid} from calendar {calendar_id}: {str(e)}"
            )
            return False, f"Error deleting event: {str(e)}"

    def get_upcoming_events(
        self, days: int = 7, limit: int = 10, calendar_id: Optional[str] = None
    ) -> Tuple[bool, Union[List[CalendarEvent], str]]:
        """
        Get upcoming events across all calendars or from a specific calendar.

        Args:
            days: Number of days to look ahead
            limit: Maximum number of events to return
            calendar_id: Optional specific calendar ID

        Returns:
            Tuple of (success, events/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to CalDAV server"

        try:
            # Set date range
            start_date = datetime.datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end_date = start_date + datetime.timedelta(days=days)

            all_events = []

            if calendar_id:
                # Get events from specific calendar
                status, events = self.get_events(calendar_id, start_date, end_date)
                if not status:
                    return False, events
                all_events = events
            else:
                # Get all calendars
                status, calendars = self.get_calendars()
                if not status:
                    return False, calendars

                # Get events from each calendar
                for cal in calendars:
                    cal_id = cal["id"]
                    status, events = self.get_events(cal_id, start_date, end_date)
                    if status:
                        all_events.extend(events)

            # Sort by start date
            all_events.sort(key=lambda e: e.start)

            # Limit the number of events
            if limit and len(all_events) > limit:
                all_events = all_events[:limit]

            return True, all_events
        except Exception as e:
            logger.error(f"Error getting upcoming events: {str(e)}")
            return False, f"Error getting upcoming events: {str(e)}"

    def search_events(
        self,
        query: str,
        start_date: Optional[datetime.datetime] = None,
        end_date: Optional[datetime.datetime] = None,
        calendar_id: Optional[str] = None,
    ) -> Tuple[bool, Union[List[CalendarEvent], str]]:
        """
        Search for events containing a keyword.

        Args:
            query: Search query
            start_date: Optional start date for search range
            end_date: Optional end date for search range
            calendar_id: Optional specific calendar ID

        Returns:
            Tuple of (success, events/error_message)
        """
        if not self._ensure_connected():
            return False, "Failed to connect to CalDAV server"

        try:
            # Set default date range if not provided
            if start_date is None:
                start_date = datetime.datetime.now().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )

            if end_date is None:
                end_date = start_date + datetime.timedelta(days=30)

            # Get events in date range
            all_events = []

            if calendar_id:
                # Get events from specific calendar
                status, events = self.get_events(calendar_id, start_date, end_date)
                if not status:
                    return False, events
                all_events = events
            else:
                # Get all calendars
                status, calendars = self.get_calendars()
                if not status:
                    return False, calendars

                # Get events from each calendar
                for cal in calendars:
                    cal_id = cal["id"]
                    status, events = self.get_events(cal_id, start_date, end_date)
                    if status:
                        all_events.extend(events)

            # Filter events by query
            query = query.lower()
            matching_events = []

            for event in all_events:
                # Match on summary, description, location
                if (
                    query in event.summary.lower()
                    or (event.description and query in event.description.lower())
                    or (event.location and query in event.location.lower())
                ):
                    matching_events.append(event)

            # Sort by start date
            matching_events.sort(key=lambda e: e.start)

            return True, matching_events
        except Exception as e:
            logger.error(f"Error searching events: {str(e)}")
            return False, f"Error searching events: {str(e)}"

    def get_today_events(
        self, calendar_id: Optional[str] = None
    ) -> Tuple[bool, Union[List[CalendarEvent], str]]:
        """
        Get today's events.

        Args:
            calendar_id: Optional specific calendar ID

        Returns:
            Tuple of (success, events/error_message)
        """
        # Calculate today's start and end
        # today = datetime.datetime.now().replace(  # Unused variable
        #     hour=0, minute=0, second=0, microsecond=0
        # )
        # tomorrow = today + datetime.timedelta(days=1)  # Unused variable

        # Get events for today
        return self.get_upcoming_events(days=1, limit=100, calendar_id=calendar_id)

    def extract_entities_from_event(self, event: CalendarEvent) -> List[Dict[str, Any]]:
        """
        Extract entities from a calendar event.

        Args:
            event: Calendar event to extract entities from

        Returns:
            List of entities with name, type, and context
        """
        entities = []

        # Create Event entity
        entities.append(
            {
                "name": event.summary,
                "entityType": "Event",
                "start": event.start.isoformat(),
                "end": event.end.isoformat(),
                "location": event.location,
                "all_day": event.all_day,
                "calendar_id": event.calendar_id,
                "context": f"Calendar event on {event.start.strftime('%Y-%m-%d')}",
            }
        )

        # Extract location as a Place entity if present
        if event.location:
            entities.append(
                {
                    "name": event.location,
                    "entityType": "Place",
                    "context": f"Location of event: {event.summary}",
                }
            )

        # Extract attendees as Contact entities
        if event.attendees:
            for attendee in event.attendees:
                entities.append(
                    {
                        "name": attendee.get("name", attendee.get("email", "")),
                        "entityType": "Contact",
                        "email": attendee.get("email", ""),
                        "role": attendee.get("role", ""),
                        "context": f"Attendee of event: {event.summary}",
                    }
                )

        # Extract organizer as a Contact entity
        if event.organizer:
            entities.append(
                {
                    "name": event.organizer.get(
                        "name", event.organizer.get("email", "")
                    ),
                    "entityType": "Contact",
                    "email": event.organizer.get("email", ""),
                    "context": f"Organizer of event: {event.summary}",
                }
            )

        # TODO: Add more sophisticated entity extraction from event description

        return entities

    def close(self):
        """Close connection to CalDAV server."""
        self.client = None
        self.principal = None
        self._calendars = None
        logger.info("Closed connection to CalDAV server")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic connection closure."""
        self.close()


# Command-line functionality for testing
if __name__ == "__main__":
    import argparse

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Proton Calendar Adapter CLI")
    parser.add_argument(
        "--action",
        choices=[
            "list-calendars",
            "list-events",
            "get-event",
            "search",
            "today",
            "create-event",
        ],
        required=True,
        help="Action to perform",
    )
    parser.add_argument("--calendar", help="Calendar ID to use")
    parser.add_argument(
        "--days", type=int, default=7, help="Number of days to look ahead"
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="Maximum number of events to retrieve"
    )
    parser.add_argument("--query", help="Search query for search action")
    parser.add_argument("--event-uid", help="Event UID for get-event action")
    parser.add_argument("--summary", help="Event summary for create-event action")
    parser.add_argument(
        "--start", help="Event start date and time (ISO format) for create-event action"
    )
    parser.add_argument(
        "--end", help="Event end date and time (ISO format) for create-event action"
    )
    parser.add_argument("--location", help="Event location for create-event action")
    parser.add_argument(
        "--description", help="Event description for create-event action"
    )
    args = parser.parse_args()

    # Create adapter instance
    adapter = ProtonCalendarAdapter()

    try:
        if args.action == "list-calendars":
            status, calendars = adapter.get_calendars()
            if status:
                print(f"Found {len(calendars)} calendars:")
                for cal in calendars:
                    print(f"- {cal['display_name']} (ID: {cal['id']})")
            else:
                print(f"Error: {calendars}")

        elif args.action == "list-events":
            if not args.calendar:
                status, events = adapter.get_upcoming_events(
                    days=args.days, limit=args.limit
                )
            else:
                status, events = adapter.get_upcoming_events(
                    days=args.days, limit=args.limit, calendar_id=args.calendar
                )

            if status:
                print(f"Found {len(events)} upcoming events:")
                for event in events:
                    print(f"- {event.summary} (Start: {event.start}, End: {event.end})")
                    if event.location:
                        print(f"  Location: {event.location}")
                    print()
            else:
                print(f"Error: {events}")

        elif args.action == "get-event":
            if not args.calendar or not args.event_uid:
                print(
                    "Error: --calendar and --event-uid are required for get-event action"
                )
                exit(1)

            status, event = adapter.get_event_by_uid(args.calendar, args.event_uid)
            if status:
                print(f"Summary: {event.summary}")
                print(f"Start: {event.start}")
                print(f"End: {event.end}")
                if event.location:
                    print(f"Location: {event.location}")
                if event.description:
                    print(f"Description: {event.description}")
                if event.attendees:
                    print("Attendees:")
                    for attendee in event.attendees:
                        print(
                            f"- {attendee.get('name', '')} ({attendee.get('email', '')})"
                        )
            else:
                print(f"Error: {event}")

        elif args.action == "search":
            if not args.query:
                print("Error: --query is required for search action")
                exit(1)

            status, events = adapter.search_events(
                args.query, calendar_id=args.calendar
            )
            if status:
                print(f"Found {len(events)} events matching '{args.query}':")
                for event in events:
                    print(f"- {event.summary} (Start: {event.start}, End: {event.end})")
                    if event.location:
                        print(f"  Location: {event.location}")
                    print()
            else:
                print(f"Error: {events}")

        elif args.action == "today":
            status, events = adapter.get_today_events(calendar_id=args.calendar)
            if status:
                print(f"Found {len(events)} events for today:")
                for event in events:
                    print(
                        f"- {event.summary} (Start: {event.start.strftime('%H:%M')}, End: {event.end.strftime('%H:%M')})"
                    )
                    if event.location:
                        print(f"  Location: {event.location}")
                    print()
            else:
                print(f"Error: {events}")

        elif args.action == "create-event":
            if not args.calendar or not args.summary or not args.start or not args.end:
                print(
                    "Error: --calendar, --summary, --start, and --end are required for create-event action"
                )
                exit(1)

            # Parse dates
            start = datetime.datetime.fromisoformat(args.start)
            end = datetime.datetime.fromisoformat(args.end)

            # Create event
            event = CalendarEvent(
                uid=str(uuid.uuid4()),
                summary=args.summary,
                description=args.description,
                start=start,
                end=end,
                location=args.location,
                calendar_id=args.calendar,
            )

            status, result = adapter.create_event(args.calendar, event)
            if status:
                print(f"Event created: {result.summary}")
                print(f"UID: {result.uid}")
            else:
                print(f"Error: {result}")

    finally:
        # Close connection
        adapter.close()
