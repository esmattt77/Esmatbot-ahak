import aiohttp
import logging
from typing import Optional, Dict, Any, List
import json
from async_utils import async_loop

logger = logging.getLogger(__name__)

class HeroSMSAPI:
    """فئة للتعامل مع API هيرو SMS المتوافق مع SMS-Activate"""
    
    BASE_URL = "https://hero-sms.com/stubs/handler_api.php"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = None
        # بدء حلقة الأحداث عند إنشاء الكائن
        async_loop.start()
    
    async def _get_session(self):
        """إنشاء جلسة HTTP إذا لم تكن موجودة"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """إغلاق جلسة HTTP"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def _make_request(self, params: Dict[str, Any]) -> str:
        """إجراء طلب إلى API"""
        try:
            session = await self._get_session()
            params['api_key'] = self.api_key
            
            async with session.get(self.BASE_URL, params=params) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"خطأ في الطلب: {response.status}")
                    return f"ERROR:{response.status}"
        except Exception as e:
            logger.error(f"استثناء في الطلب: {e}")
            return f"ERROR:EXCEPTION"
    
    def get_balance_sync(self) -> float:
        """نسخة متزامنة من get_balance"""
        return async_loop.run_coroutine(self.get_balance())
    
    async def get_balance(self) -> float:
        """الحصول على الرصيد الحالي"""
        result = await self._make_request({'action': 'getBalance'})
        
        if result.startswith('ACCESS_BALANCE:'):
            balance_str = result.split(':')[1]
            return float(balance_str)
        return 0.0
    
    def get_number_sync(self, service: str, country: int = 6) -> Optional[Dict[str, Any]]:
        """نسخة متزامنة من get_number"""
        return async_loop.run_coroutine(self.get_number(service, country))
    
    async def get_number(self, service: str, country: int = 6) -> Optional[Dict[str, Any]]:
        """
        طلب رقم جديد للخدمة المحددة
        API يعيد نصاً بالصيغة: ACCESS_NUMBER:123456789:79584******
        """
        params = {
            'action': 'getNumber',
            'service': service,
            'country': country
        }
        
        try:
            result = await self._make_request(params)
            logger.info(f"📞 استجابة getNumber: {result}")
            
            # تحليل الاستجابة
            if result.startswith('ACCESS_NUMBER:'):
                parts = result.split(':')
                if len(parts) >= 3:
                    activation_id = parts[1]
                    phone_number = parts[2]
                    return {
                        'activationId': activation_id,
                        'phoneNumber': phone_number,
                        'success': True
                    }
            elif result.startswith('NO_NUMBERS'):
                logger.error("❌ لا توجد أرقام متاحة لهذه الخدمة")
                return {'error': 'no_numbers', 'success': False}
            elif result.startswith('NO_BALANCE'):
                logger.error("❌ رصيد غير كافٍ")
                return {'error': 'no_balance', 'success': False}
            elif result.startswith('BAD_SERVICE'):
                logger.error("❌ خدمة غير صالحة")
                return {'error': 'bad_service', 'success': False}
            else:
                logger.error(f"❌ استجابة غير متوقعة: {result}")
                return {'error': 'unknown', 'response': result, 'success': False}
                
        except Exception as e:
            logger.error(f"❌ استثناء في طلب الرقم: {e}")
            return {'error': str(e), 'success': False}
    
    def get_prices_sync(self, service: str = None) -> Dict:
        """نسخة متزامنة من get_prices"""
        return async_loop.run_coroutine(self.get_prices(service))
    
    async def get_prices(self, service: str = None) -> Dict:
        """الحصول على الأسعار الحقيقية من API"""
        params = {'action': 'getPrices'}
        if service:
            params['service'] = service
            
        try:
            result = await self._make_request(params)
            if result.startswith('ERROR'):
                return {}
            
            try:
                data = json.loads(result)
                logger.info(f"✅ تم جلب الأسعار بنجاح: {len(data)} دولة")
                return data
            except json.JSONDecodeError:
                logger.error(f"❌ فشل تحليل JSON: {result[:200]}")
                return {}
        except Exception as e:
            logger.error(f"❌ استثناء في جلب الأسعار: {e}")
            return {}
