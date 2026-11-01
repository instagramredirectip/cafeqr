from django.shortcuts import render
from .models import Restaurant

def platform_home_view(request):
    """
    Public landing page for the platform with links to demo restaurants and owner portal.
    """
    restaurants = Restaurant.objects.filter(is_active=True).order_by('name')
    return render(request, 'ordering/home.html', {'restaurants': restaurants})

