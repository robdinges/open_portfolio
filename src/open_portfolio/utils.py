from datetime import date, timedelta
from typing import Optional
import logging

class TimeTravel:
    """Helper for simulating the passage of time.

    ``current_date`` starts at ``date.today()`` but can be moved forward.
    """

    def __init__(self, start_date: Optional[date] = None):
        self.current_date = start_date or date.today()

    def skip_days(self, days: int = 1) -> date:
        if days <= 0:
            raise ValueError("Number of days to skip must be positive")
        self.current_date += timedelta(days=days)
        logging.debug("Skipped %s days; new date %s", days, self.current_date)
        return self.current_date

    def is_weekend(self, d: date) -> bool:
        return d.weekday() >= 5

    def skip_working_days(self, days: int = 1) -> date:
        if days <= 0:
            raise ValueError("Number of working days to skip must be positive")
        skipped = 0
        while skipped < days:
            self.current_date += timedelta(days=1)
            if not self.is_weekend(self.current_date):
                skipped += 1
        return self.current_date

    def go_to(self, new_date: date) -> date:
        if new_date <= self.current_date:
            raise ValueError("New date must be after current date")
        if self.is_weekend(new_date):
            raise ValueError("New date must not be a weekend")
        self.current_date = new_date
        logging.debug("Moved to new date: %s", self.current_date)
        return self.current_date
