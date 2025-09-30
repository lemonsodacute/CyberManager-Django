# dashboard/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.conf import settings 

# Import API View (có thể để lại ở đây vì nó chỉ tham chiếu class)
from .api_views import DashboardSummaryAPIView 

class DashboardConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        # Chúng ta không thể import AnonymousUser ở đây, nên phải lấy nó từ scope
        user = self.scope.get('user')
        
        # 1. KIỂM TRA QUYỀN TRUY CẬP 
        # is_authenticated sẽ là False nếu AuthMiddlewareStack không tìm thấy Session/User
        if user is None or not user.is_authenticated or not user.is_staff:
            await self.close() # Đóng kết nối nếu không phải Staff/Admin
            return

        # 2. XỬ LÝ KẾT NỐI
        self.group_name = 'dashboard_summary' 

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

        # 3. GỬI DỮ LIỆU BAN ĐẦU
        initial_data = await self.get_summary_data()
        await self.send(text_data=json.dumps({
            'type': 'initial_summary',
            'data': initial_data
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def send_summary_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'summary_update',
            'data': event['data']
        }))

    @sync_to_async
    def get_summary_data(self):
        # <<< CÁC IMPORTS CẦN THIẾT PHẢI Ở TRONG HÀM NÀY >>>
        from django.test import RequestFactory 
        from django.contrib.auth.models import AnonymousUser 
        
        # 1. Lấy user từ scope
        # AnonymousUser chỉ được import ở đây
        user = self.scope.get('user', AnonymousUser())
        
        # 2. Tạo request giả
        factory = RequestFactory()
        fake_request = factory.get('/api/dashboard/summary/') 
        fake_request.user = user

        # 3. Gọi calculate_summary đã tách
        return DashboardSummaryAPIView().calculate_summary()