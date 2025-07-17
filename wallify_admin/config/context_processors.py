from django.conf import settings

def settings_context(request):
    """
    Context processor to make settings available in templates.
    """
    return {
        'settings': settings
    } 