# shop/middleware.py

from django.shortcuts import redirect
from django.urls import reverse, resolve, Resolver404
from django.utils import timezone
from django.conf import settings
from .models import SiteEvent # Assuming your SiteEvent model is in shop.models

class PreLaunchRestrictionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.
        self.allowed_url_names = [
            'competition_page', 
            'submit_competition_code',
            'login', 
            'signup', 
            'logout',
            'password_reset', # Add if you have password reset functionality
            'password_reset_done',
            'password_reset_confirm',
            'password_reset_complete',
            # Add any other public utility views by name if needed
        ]
        self.allowed_path_prefixes = [
            settings.STATIC_URL, # Allow access to static files
            settings.MEDIA_URL,  # Allow access to media files
            '/admin/',           # Allow access to the admin interface
            # Add other path prefixes if necessary (e.g., '/api/public/')
        ]

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        # Allow superusers to access any page
        if request.user.is_authenticated and request.user.is_superuser:
            return self.get_response(request)

        launch_event = SiteEvent.objects.filter(event_name='SITE_LAUNCH', is_active=True).order_by('-event_datetime').first()

        if launch_event and launch_event.event_datetime > timezone.now():
            # Site has not launched yet
            current_path = request.path_info
            
            # Check if the current path starts with any allowed prefixes
            is_path_allowed_by_prefix = any(current_path.startswith(prefix) for prefix in self.allowed_path_prefixes if prefix) # Ensure prefix is not None

            if is_path_allowed_by_prefix:
                return self.get_response(request)

            # Resolve the current path to a URL name to check against allowed names
            try:
                resolver_match = resolve(current_path)
                current_url_name = resolver_match.url_name
                if current_url_name in self.allowed_url_names:
                    return self.get_response(request)
            except Resolver404:
                # Path doesn't resolve to a named URL, might be a direct file or unhandled.
                # If not covered by prefixes, it will be redirected.
                pass
            
            # If not an allowed path or URL name, redirect to competition page
            # unless it's already the competition page to avoid redirect loop
            if current_path != reverse('competition_page'):
                print(f"Pre-launch: Redirecting from {current_path} to competition page.") # For debugging
                return redirect('competition_page')

        return self.get_response(request)


# +++ Your Custom Middleware +++
'shop.middleware.PreLaunchRestrictionMiddleware', 
# +++ End Custom Middleware +++