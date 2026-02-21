"""Dashboard package exports."""

from safeai.dashboard.routes import router
from safeai.dashboard.service import DashboardPrincipal, DashboardService

__all__ = ["router", "DashboardPrincipal", "DashboardService"]
