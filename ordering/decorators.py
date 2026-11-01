from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from .models import RestaurantStaff

def restaurant_staff_required(view_func):
    """
    Decorator that verifies:
    1. User is authenticated.
    2. User is linked to an active RestaurantStaff profile.
    3. Staff member's restaurant is active.
    Attaches `request.staff` and `request.restaurant` to the request object.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Please log in to access the restaurant owner dashboard.")
            return redirect('owner_login')

        try:
            staff = RestaurantStaff.objects.select_related('restaurant').get(
                user=request.user,
                is_active=True,
                restaurant__is_active=True
            )
            request.staff = staff
            request.restaurant = staff.restaurant
        except RestaurantStaff.DoesNotExist:
            messages.error(request, "Access denied: You do not have an active restaurant owner profile.")
            return redirect('owner_login')

        return view_func(request, *args, **kwargs)
    return _wrapped_view

