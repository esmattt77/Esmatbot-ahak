import requests
import logging
from typing import Optional, Dict, Any, List
import json
import time

logger = logging.getLogger(__name__)

class HeroSMSAPI:
    """فئة للتعامل مع API هيرو SMS باستخدام requests (متزامن)"""
    
    BASE_URL = "https://hero-sms.com/stubs/handler_api.php"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        logger.info("✅ تم تهيئة API client (متزامن)")
    
    def _make_request(self, params: Dict[str, Any]) -> str:
        """إجراء طلب متزامن إلى API"""
        params['api_key'] = self.api_key
        
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"خطأ في الطلب: {response.status_code}")
                return f"ERROR:{response.status_code}"
        except requests.exceptions.Timeout:
            logger.error("⏱️ timeout في الطلب")
            return "ERROR:TIMEOUT"
        except Exception as e:
            logger.error(f"استثناء في الطلب: {e}")
            return f"ERROR:EXCEPTION"
    
    def get_balance(self) -> float:
        """الحصول على الرصيد الحالي"""
        result = self._make_request({'action': 'getBalance'})
        
        if result.startswith('ACCESS_BALANCE:'):
            balance_str = result.split(':')[1]
            return float(balance_str)
        return 0.0
    
    def get_number(self, service: str, country: int = 6) -> Optional[Dict[str, Any]]:
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
            result = self._make_request(params)
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
                return {'error': 'no_numbers', 'success': False, 'message': 'لا توجد أرقام متاحة'}
            elif result.startswith('NO_BALANCE'):
                logger.error("❌ رصيد غير كافٍ")
                return {'error': 'no_balance', 'success': False, 'message': 'رصيد API غير كافٍ'}
            elif result.startswith('BAD_SERVICE'):
                logger.error("❌ خدمة غير صالحة")
                return {'error': 'bad_service', 'success': False, 'message': 'خدمة غير صالحة'}
            elif result.startswith('ERROR'):
                return {'error': 'api_error', 'success': False, 'message': 'خطأ في API'}
            else:
                logger.error(f"❌ استجابة غير متوقعة: {result}")
                return {'error': 'unknown', 'success': False, 'message': 'استجابة غير معروفة'}
                
        except Exception as e:
            logger.error(f"❌ استثناء في طلب الرقم: {e}")
            return {'error': str(e), 'success': False, 'message': f'استثناء: {str(e)}'}
    
    def get_prices(self, service: str = None) -> Dict:
        """الحصول على الأسعار من API"""
        params = {'action': 'getPrices'}
        if service:
            params['service'] = service
            
        try:
            result = self._make_request(params)
            if result.startswith('ERROR'):
                return {}
            
            try:
                data = json.loads(result)
                logger.info(f"✅ تم جلب الأسعار بنجاح: {len(data)} دولة")
                return data
            except json.JSONDecodeError:
                logger.error(f"❌ فشل تحليل JSON")
                return {}
        except Exception as e:
            logger.error(f"❌ استثناء في جلب الأسعار: {e}")
            return {}
    
    def get_services(self) -> List[Dict[str, str]]:
        """الحصول على قائمة الخدمات المتاحة"""
        params = {'action': 'getServicesList'}
        
        try:
            result = self._make_request(params)
            try:
                data = json.loads(result)
                if data.get('status') == 'success':
                    return data.get('services', [])
            except:
                pass
            return []
        except Exception as e:
            logger.error(f"خطأ في جلب الخدمات: {e}")
            return []
