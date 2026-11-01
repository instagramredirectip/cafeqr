from django.conf import settings

def platform_context(request):
    """Provides global site variables to all templates."""
    return {
        'SITE_BASE_URL': getattr(settings, 'SITE_BASE_URL', 'http://127.0.0.1:8000'),
        'PLATFORM_NAME': 'DineFlow QR & Restaurant Suite',
    }

