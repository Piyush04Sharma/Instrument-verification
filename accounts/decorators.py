from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .utils import get_profile


def role_required(*roles):
    """Allow a view only for logged-in users whose profile role is in `roles`."""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if get_profile(request.user).role in roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied

        return _wrapped

    return decorator
