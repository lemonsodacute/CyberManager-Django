# quanly/routing.py

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Đây là nơi bạn định nghĩa các websocket của app quanly (nếu có)
]

# Định nghĩa một Worker Route (Không phải WebSocket)
worker_urlpatterns = [
    re_path(r'^worker/auto_shutdown/$', consumers.AutoShutdownConsumer.as_asgi()),
]