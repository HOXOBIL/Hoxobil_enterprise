# shop/apps.py
from django.apps import AppConfig

class ShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shop'

    def ready(self):
        import shop.signals # Import your signals module
        # The post_save signal for UserProfile creation is now in models.py
        # If you move other signals to shop/signals.py, ensure they are connected here or in models.py
        print("ShopConfig ready, signals should be imported.")
