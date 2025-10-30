from django.apps import AppConfig

class QuanLyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'quanly'

    def ready(self):
        """
        Khởi tạo APScheduler sau khi chắc chắn DB và bảng APScheduler đã tồn tại.
        """
        import atexit
        from django.db.utils import OperationalError, ProgrammingError

        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from django_apscheduler.jobstores import DjangoJobStore
            from .tasks import auto_shutdown_prepaid_sessions

            scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")

            # ⚠️ Kiểm tra bảng APScheduler đã tồn tại chưa
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    SHOW TABLES LIKE 'django_apscheduler_djangojob';
                """)
                result = cursor.fetchone()

            if not result:
                print("[⚠️ APScheduler] Bảng django_apscheduler_djangojob chưa tồn tại. Bỏ qua scheduler lần này.")
                return

            scheduler.add_jobstore(DjangoJobStore(), "default")
            scheduler.add_job(
                auto_shutdown_prepaid_sessions,
                trigger="interval",
                seconds=30,
                id="auto_shutdown_sessions",
                replace_existing=True,
            )
            scheduler.start()
            print("[✅ APScheduler] Auto shutdown sessions scheduler started (every 30s).")

            atexit.register(lambda: scheduler.shutdown(wait=False))

        except (OperationalError, ProgrammingError):
            # Tránh lỗi khi DB chưa sẵn sàng
            print("[⚠️ APScheduler] Database chưa sẵn sàng, bỏ qua scheduler.")
        except Exception as e:
            print(f"[❌ APScheduler] Lỗi khởi tạo scheduler: {e}")
