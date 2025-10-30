# quanlynet/asgi.py

import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quanlynet.settings')

django_asgi_app = get_asgi_application() 

import dashboard.routing
import quanly.routing # <<< THÊM DÒNG NÀY

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack( 
        URLRouter(
            dashboard.routing.websocket_urlpatterns + # KẾT HỢP VỚI DASHBOARD
            quanly.routing.websocket_urlpatterns
        )
    ),
    # <<< THÊM WORKER PROTOCOL NÀY >>>
    "channel": URLRouter(
        quanly.routing.worker_urlpatterns
    )
    # <<< KẾT THÚC THÊM WORKER PROTOCOL >>>
})