from accounts.utils import get_profile

from .models import Notification


def site_context(request):
    """Adds the user's role and unread notification count to every template."""
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return {
            "user_role": get_profile(user).role,
            "unread_count": Notification.objects.filter(user=user, is_read=False).count(),
        }
    return {"user_role": None, "unread_count": 0}
