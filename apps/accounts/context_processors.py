from .models import Role
from .permissions import get_accessible_activities, get_user_memberships, user_is_global


def navigation_context(request):
    """Expose la première activité autorisée pour la navigation commune."""
    activities = get_accessible_activities(request.user)
    can_manage_team = request.user.is_authenticated and get_user_memberships(
        request.user
    ).filter(role=Role.MANAGER, activity__is_active=True).exists()
    memberships = get_user_memberships(request.user)
    employee_mode = (
        request.user.is_authenticated
        and memberships.count() == 1
        and memberships.filter(role=Role.EMPLOYEE).exists()
    )
    return {
        "nav_activity": activities.first(),
        "nav_can_manage_team": can_manage_team,
        "nav_is_global": user_is_global(request.user),
        "nav_employee_mode": employee_mode,
    }