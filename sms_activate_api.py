import aiohttp
import logging
from typing import Optional, Dict, Any, List
import json

logger = logging.getLogger(__name__)

class HeroSMSAPI:
    """فئة للتعامل مع API هيرو SMS المتوافق مع SMS-Activate"""
    
    BASE_URL = "https://hero-sms.com/stubs/handler_api.php"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = None
        
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
    
    async def get_balance(self) -> float:
        """الحصول على الرصيد الحالي - هذه تعمل بشكل صحيح"""
        result = await self._make_request({'action': 'getBalance'})
        
        if result.startswith('ACCESS_BALANCE:'):
            balance_str = result.split(':')[1]
            return float(balance_str)
        return 0.0
    
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
    
    async def get_number_v2(self, service: str, country: int = 6) -> Optional[Dict[str, Any]]:
        """نسخة V2 من طلب الرقم (ترجع JSON)"""
        params = {
            'action': 'getNumberV2',
            'service': service,
            'country': country
        }
        
        try:
            session = await self._get_session()
            params['api_key'] = self.api_key
            
            async with session.get(self.BASE_URL, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"خطأ في طلب الرقم V2: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"استثناء في طلب الرقم V2: {e}")
            return None
    
    async def get_status(self, activation_id: int) -> str:
        """الحصول على حالة التفعيل"""
        params = {
            'action': 'getStatus',
            'id': activation_id
        }
        
        return await self._make_request(params)
    
    async def set_status(self, activation_id: int, status: int) -> bool:
        """تغيير حالة التفعيل (3: طلب إعادة SMS, 6: إكمال, 8: إلغاء)"""
        params = {
            'action': 'setStatus',
            'id': activation_id,
            'status': status
        }
        
        result = await self._make_request(params)
        return result == 'ACCESS_READY'
    
    async def get_services(self) -> List[Dict[str, str]]:
        """الحصول على قائمة الخدمات المتاحة"""
        params = {'action': 'getServicesList'}
        
        try:
            session = await self._get_session()
            params['api_key'] = self.api_key
            
            async with session.get(self.BASE_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'success':
                        return data.get('services', [])
                return []
        except Exception as e:
            logger.error(f"خطأ في جلب الخدمات: {e}")
            return []
    
    async def get_prices(self, service: str = None) -> Dict:
        """
        الحصول على الأسعار الحقيقية من API
        ترجع قاموساً برموز الدول وأسعارها
        """
        params = {'action': 'getPrices'}
        if service:
            params['service'] = service
            
        try:
            session = await self._get_session()
            params['api_key'] = self.api_key
            
            async with session.get(self.BASE_URL, params=params) as response:
                if response.status == 200:
                    text = await response.text()
                    # محاولة تحليل JSON
                    try:
                        data = json.loads(text)
                        logger.info(f"✅ تم جلب الأسعار بنجاح: {len(data)} دولة")
                        return data
                    except json.JSONDecodeError:
                        logger.error(f"❌ فشل تحليل JSON: {text[:200]}")
                        return {}
                else:
                    logger.error(f"❌ خطأ في جلب الأسعار: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"❌ استثناء في جلب الأسعار: {e}")
            return {}
    
    async def get_countries(self) -> List[Dict]:
        """الحصول على قائمة الدول المتاحة"""
        params = {'action': 'getCountries'}
        
        try:
            session = await self._get_session()
            params['api_key'] = self.api_key
            
            async with session.get(self.BASE_URL, params=params) as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            logger.error(f"خطأ في جلب الدول: {e}")
            return []
