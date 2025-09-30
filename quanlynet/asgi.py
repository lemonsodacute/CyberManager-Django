# quanlynet/asgi.py

"""
ASGI config for quanlynet project.
"""

import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# Dòng quan trọng phải nằm ở đây để Django biết file settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quanlynet.settings')

# 1. Khởi tạo Django ASGI ứng dụng (HTTP)
django_asgi_app = get_asgi_application() 

# 2. Import routing của bạn (sau khi settings và apps đã được load)
import dashboard.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app, # SỬ DỤNG BIẾN ĐÃ ĐƯỢC GỌI
    "websocket": AuthMiddlewareStack( 
        URLRouter(
            dashboard.routing.websocket_urlpatterns
        )
    ),
})