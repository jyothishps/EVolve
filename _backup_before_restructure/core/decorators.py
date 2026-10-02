from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    """
    Restrict view to logged-in users with role=ADMIN.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('core:login')
        if not request.user.is_admin():
            messages.error(request, 'Access denied. Admins only.')
            return redirect('core:driver_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper