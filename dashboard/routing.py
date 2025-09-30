# dashboard/routing.py

from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    # Đường dẫn WebSocket sẽ là ws://localhost:8000/ws/dashboard/summary/
    re_path(r'ws/dashboard/summary/$', consumers.DashboardConsumer.as_asgi()),
]