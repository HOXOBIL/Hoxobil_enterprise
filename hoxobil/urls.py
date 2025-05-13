from django.contrib import admin
from django.urls import path, include  # ✅ make sure include is imported

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('shop.urls')),  # ✅ this connects all URLs from the shop app
]
