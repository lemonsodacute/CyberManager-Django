# CyberManager - Quản lý quán net

Đây là project mình làm để thực hành xây dựng một hệ thống quản lý quán net bằng Django. Mình tập trung vào các chức năng quản lý máy, tính tiền theo thời gian sử dụng và quản lý hoạt động trong quán.

## Chức năng chính

- Quản lý tài khoản theo vai trò admin, nhân viên và khách hàng
- Theo dõi máy trống, máy đang sử dụng và máy bị hỏng
- Quản lý phiên sử dụng máy, tính tiền giờ và kiểm tra số dư khách hàng
- Hỗ trợ bán dịch vụ tại quầy (POS), tạo đơn và hóa đơn
- Quản lý menu, nguyên liệu, tồn kho và khuyến mãi
- Quản lý ca làm của nhân viên, giao dịch và doanh thu
- Cập nhật một số dữ liệu dashboard qua WebSocket
- Có phần xử lý tự động kết thúc phiên trả trước khi không đủ số dư

## Công nghệ sử dụng

- Backend: Python, Django, Django REST Framework
- Database: MySQL
- Giao diện: Django Templates, HTML/CSS/JavaScript, Jazzmin cho trang quản trị
- Realtime: Django Channels, Redis
- Xử lý định kỳ: APScheduler

## Cách chạy trên máy cá nhân

Mình dùng Python và MySQL để chạy project. Các lệnh dưới đây viết cho PowerShell trên Windows.

- Clone repo và mở thư mục project:

```powershell
git clone https://github.com/lemonsodacute/CyberManager-Django.git
cd CyberManager-Django
```

- Tạo môi trường Python và cài thư viện:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

- Tạo database MySQL tên `quanlynet_db` (có thể đổi tên bằng biến môi trường)
- Tạo secret key riêng cho máy, không chép key thật vào mã nguồn:

```powershell
$env:DJANGO_SECRET_KEY = python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
$env:DJANGO_DEBUG = "True"
$env:MYSQL_DATABASE = "quanlynet_db"
$env:MYSQL_USER = "root"
$env:MYSQL_PASSWORD = "MAT_KHAU_MYSQL_CUA_BAN"
$env:MYSQL_HOST = "localhost"
$env:MYSQL_PORT = "3306"
```

- Chạy Redis trên cổng 6380 nếu dùng các chức năng WebSocket. Ví dụ máy có Docker:

```powershell
docker run --name cybermanager-redis -d -p 6380:6379 redis:7
```

- Tạo bảng, tài khoản quản trị và khởi động ứng dụng:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- Mở `http://127.0.0.1:8000/` để vào trang đăng nhập
- Khi cần chạy phần WebSocket bằng ASGI, có thể dùng `daphne -b 127.0.0.1 -p 8000 quanlynet.asgi:application` thay cho lệnh `runserver`

## Kiểm tra cơ bản

- Lệnh kiểm tra cấu hình: `python manage.py check`
- Lệnh chạy test: `python manage.py test`
- Các bài test hiện tại mới kiểm tra một số trường hợp cơ bản về tài khoản và phân quyền, chưa bao phủ toàn bộ chức năng POS, kho và thanh toán

## Ghi chú

- Đây là đồ án thực hành nên vẫn còn một số phần cần chỉnh lại và bổ sung kiểm thử
- `DJANGO_SECRET_KEY` là bắt buộc để chạy project, `DJANGO_DEBUG` mặc định là `False`
- Không đẩy mật khẩu, secret key hoặc file `.env` lên GitHub
- Nếu từng sử dụng key cũ đã xuất hiện trong GitHub, cần thay key đó khi sử dụng hoặc triển khai
- Khi đưa lên server thật cần cấu hình lại domain, database, Redis, static files và HTTPS
