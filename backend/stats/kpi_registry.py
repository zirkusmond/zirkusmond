"""KPI (Key Performance Indicator) registry following the Open-Closed Principle.

Add new KPIs by creating a KPI class and registering it — no need to modify core logic.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from .period_comparison import format_comparison_footer


class KPI(ABC):
    """Base class for dashboard KPIs.

    Subclass this and implement calculate() to add a new KPI. Optionally override
    format_metric() to customize display (e.g., add currency symbols, percentages, durations).
    Set supports_comparison=False to disable period-over-period comparison.
    """

    title: str
    key: str  # Used to look up previous period value in prev_metrics dict
    supports_comparison: bool = True

    @abstractmethod
    def calculate(self, since: datetime | None) -> Any:
        """Calculate the KPI value for the current period (since the given datetime).

        Args:
            since: Start of the current period, or None for all-time.

        Returns:
            The raw metric value (int, float, timedelta, etc.)
        """
        pass

    def format_metric(self, value: Any) -> str | int | float:
        """Format the calculated value for display.

        Override this to add units, currency symbols, or custom formatting.
        Default: returns the value as-is.
        """
        return value

    def get_comparison_value(self, current: Any, previous: Any | None) -> str | None:
        """Generate a comparison footer showing change vs. previous period.

        Override this if you need custom comparison logic.
        Default: uses format_comparison_footer() if supports_comparison=True.
        """
        if not self.supports_comparison or previous is None:
            return None
        return format_comparison_footer(current, previous)

    def render(
        self, since: datetime | None, previous_metrics: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Render the complete KPI card data (title, metric, footer).

        Called by the dashboard; you usually don't need to override this.
        """
        raw_value = self.calculate(since)
        formatted_value = self.format_metric(raw_value)

        footer = None
        if previous_metrics and self.supports_comparison:
            previous_value = previous_metrics.get(self.key)
            footer = self.get_comparison_value(raw_value, previous_value)

        return {
            "title": self.title,
            "metric": formatted_value,
            "footer": footer,
        }


class KPIRegistry:
    """Registry for all dashboard KPIs.

    Call register() to add a KPI, then get_all() to retrieve them in order.
    """

    def __init__(self):
        self._kpis: list[KPI] = []

    def register(self, kpi: KPI) -> None:
        """Register a KPI instance. KPIs are rendered in registration order."""
        self._kpis.append(kpi)

    def get_all(self) -> list[KPI]:
        """Return all registered KPIs in order."""
        return self._kpis


# Global registry instance
registry = KPIRegistry()
