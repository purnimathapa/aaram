"""The single staff-only guard used by every dashboard view.

Putting the check in one decorator means every /staff/ page is protected the
same way: visitors are sent to the login page, and logged-in customers who are
not staff get a 403 Forbidden.
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def staff_required(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped
