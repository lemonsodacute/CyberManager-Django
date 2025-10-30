# quanly/consumers.py

import asyncio
from datetime import timezone
from channels.consumer import AsyncConsumer
from asgiref.sync import sync_to_async
from django.utils import timezone # <<< THÊM DÒNG NÀY

# Import task của chúng ta
from .tasks import auto_shutdown_prepaid_sessions 

class AutoShutdownConsumer(AsyncConsumer):
    
    async def connect(self):
        # Không cần kết nối WebSocket, chỉ cần chạy task
        pass 
        
    async def disconnect(self, close_code):
        # Không cần xử lý khi ngắt
        pass 
        
    # <<< THÊM PHƯƠNG THỨC NÀY ĐỂ KÍCH HOẠT VÒNG LẶP >>>
    async def __aenter__(self):
        # Phương thức này được gọi khi Consumer khởi động
        self.task = asyncio.create_task(self.run_task({}))
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # Phương thức này được gọi khi Consumer ngắt
        self.task.cancel()
        
    async def run_task(self, event):
        while True:
            # Gọi hàm kiểm tra ngắt phiên
            try:
                shutdown_count = await sync_to_async(auto_shutdown_prepaid_sessions)()
                if shutdown_count > 0:
                    print(f"[{timezone.now().strftime('%H:%M:%S')}] Auto-Shutdown: Đã ngắt {shutdown_count} phiên trả trước.")
            except Exception as e:
                print(f"Lỗi trong worker loop: {e}")
            
            # Chờ 30 giây trước khi kiểm tra lần tiếp theo
            await asyncio.sleep(30) 
            
            
    async def connect(self):
        # Không cần kết nối WebSocket, chỉ cần chạy task
        pass 
        
    async def disconnect(self, close_code):
        # Không cần xử lý khi ngắt
        pass