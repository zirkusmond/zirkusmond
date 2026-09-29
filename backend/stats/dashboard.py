from .kpi_registry import registry
from .kpis import *  # noqa: F401, F403 - imports register KPIs into the global registry
from .period_comparison import calculate_previous_period_bounds, get_previous_period_metrics
from .ranges import range_navigation_items, range_since, resolve_range


def dashboard_callback(request, context):
    """Injects the KPI cards and range switcher shown above the charts on the admin
    index/dashboard page.

    Registered via UNFOLD["DASHBOARD_CALLBACK"] in config/settings/unfold_config.py; consumed by
    templates/admin/index.html. The charts pull their own data independently (same selected
    range, read straight off the request) via the registered components in stats/components.py.

    KPIs are defined in stats/kpis.py and automatically registered. To add a new KPI:
    1. Create a new KPI subclass in stats/kpis.py
    2. Implement the calculate() method
    3. Optionally override format_metric() for custom formatting
    4. Register it at the bottom of stats/kpis.py
    """
    range_spec = resolve_range(request)
    since = range_since(range_spec)

    # Calculate previous period bounds for comparison
    previous_since, previous_until = calculate_previous_period_bounds(range_spec, since)
    prev_metrics = get_previous_period_metrics(previous_since, previous_until)

    # Render all registered KPIs
    kpis = [kpi.render(since, prev_metrics) for kpi in registry.get_all()]

    context.update(
        {
            "range_options": range_navigation_items(request, active=range_spec),
            "kpis": kpis,
            "visits_chart_title": "Visits (excluding bots)",
            "device_chart_title": "Sessions by device",
        }
    )
    return context
