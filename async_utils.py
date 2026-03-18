import asyncio
import threading
import logging

logger = logging.getLogger(__name__)

class AsyncLoop:
    """فئة لإدارة حلقة أحداث واحدة دائمة في خيط منفصل"""
    
    _instance = None
    _loop = None
    _thread = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def start(self):
        """بدء حلقة الأحداث في خيط منفصل"""
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            logger.info("✅ تم بدء حلقة الأحداث الدائمة")
    
    def _run_loop(self):
        """تشغيل حلقة الأحداث إلى الأبد"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()
    
    def get_loop(self):
        """الحصول على حلقة الأحداث"""
        return self._loop
    
    def run_coroutine(self, coro):
        """تشغيل كوروتين في حلقة الأحداث"""
        if not self._loop or not self._loop.is_running():
            self.start()
            # انتظر قليلاً حتى تبدأ الحلقة
            import time
            time.sleep(0.1)
        
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=30)

# إنشاء كائن عام
async_loop = AsyncLoop()
