# sms_activate_api.py

import requests
import json
from typing import Dict, List, Optional, Union

class RequestError(Exception):
    def __init__(self, error_code: str):
        self.error_code = error_code
        self.error_codes = {
            'ACCESS_ACTIVATION': 'الخدمة مفعلة بنجاح',
            'ACCESS_CANCEL': 'تم إلغاء التفعيل',
            'ACCESS_READY': 'في انتظار الرسالة الجديدة',
            'ACCESS_RETRY_GET': 'تم تأكيد جاهزية الرقم',
            'ACCOUNT_INACTIVE': 'لا توجد أرقام متاحة',
            'ALREADY_FINISH': 'الاستئجار انتهى بالفعل',
            'ALREADY_CANCEL': 'الاستئجار ألغي بالفعل',
            'BAD_ACTION': 'إجراء غير صحيح (معامل action)',
            'BAD_SERVICE': 'اسم الخدمة غير صحيح (معامل service)',
            'BAD_KEY': 'مفتاح API غير صحيح',
            'BAD_STATUS': 'محاولة تعيين حالة غير موجودة',
            'BANNED': 'الحساب محظور',
            'CANT_CANCEL': 'لا يمكن إلغاء الاستئجار (مرت أكثر من 20 دقيقة)',
            'ERROR_SQL': 'أحد المعاملات له قيمة غير مسموحة',
            'NO_NUMBERS': 'لا توجد أرقام مجانية لاستقبال الرسائل من الخدمة الحالية',
            'NO_BALANCE': 'انتهى الرصيد',
            'NO_YULA_MAIL': 'يجب أن يكون لديك أكثر من 500 روبل في الحساب لشراء خدمات',
            'NO_CONNECTION': 'لا يوجد اتصال بخوادم sms-activate',
            'NO_ID_RENT': 'لم يتم تحديد معرف الاستئجار',
            'NO_ACTIVATION': 'معرف التفعيل المحدد غير موجود',
            'STATUS_CANCEL': 'تم إلغاء التفعيل/الاستئجار',
            'STATUS_FINISH': 'تم دفع الاستئجار وإنهاؤه',
            'STATUS_WAIT_CODE': 'في انتظار أول رسالة',
            'STATUS_WAIT_RETRY': 'في انتظار تأكيد الرمز',
            'SQL_ERROR': 'أحد المعاملات له قيمة غير مسموحة',
            'INVALID_PHONE': 'الرقم غير مملوك لك (معرف استئجار خاطئ)',
            'INCORECT_STATUS': 'الحالة غير موجودة أو محددة بشكل غير صحيح',
            'WRONG_SERVICE': 'الخدمة لا تدعم إعادة التوجيه',
            'WRONG_SECURITY': 'خطأ في محاولة نقل معرف التفعيل بدون إعادة توجيه'
        }
        message = self.error_codes.get(error_code, f"خطأ غير معروف: {error_code}")
        super().__init__(message)

class SMSActivate:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = 'https://api.sms-activate.org/stubs/handler_api.php'
        self.session = requests.Session()

    def _request(self, params: Dict, method: str = 'GET', parse_json: bool = False, get_number: Optional[int] = None):
        params['api_key'] = self.api_key
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(self.base_url, params=params)
            else:
                response = self.session.post(self.base_url, data=params)
            
            result = response.text.strip()
            
            # التحقق من وجود خطأ
            if result in RequestError({}).error_codes:
                raise RequestError(result)
            
            if parse_json:
                return json.loads(result)
            
            if get_number == 1:
                parts = result.split(':')
                return {'id': parts[1], 'number': parts[2]}
            elif get_number == 2:
                parts = result.split(':')
                return {'status': parts[0], 'code': parts[1] if len(parts) > 1 else None}
            elif get_number == 3:
                parts = result.split(':')
                return {'status': parts[0]}
            else:
                return result
                
        except RequestError as e:
            raise e
        except Exception as e:
            raise RequestError('NO_CONNECTION')

    def get_balance(self) -> float:
        """الحصول على الرصيد"""
        result = self._request({'action': 'getBalance'})
        return float(result)

    def get_balance_and_cashback(self) -> Dict:
        """الحصول على الرصيد والكاش باك"""
        result = self._request({'action': 'getBalanceAndCashBack'})
        parts = result.split(':')
        return {'balance': float(parts[0]), 'cashback': float(parts[1])}

    def get_numbers_status(self, country: Optional[int] = None, operator: Optional[str] = None) -> Dict:
        """الحصول على حالة الأرقام"""
        params = {'action': 'getNumbersStatus'}
        if country is not None:
            params['country'] = country
        if operator:
            params['operator'] = operator
            
        result = self._request(params, parse_json=True)
        response = {}
        for service, count in result.items():
            service_clean = service.rstrip('_01')
            response[service_clean] = count
        return response

    def get_number(self, service: str, country: Optional[int] = None, forward: int = 0, 
                   operator: Optional[str] = None, ref: Optional[str] = None) -> Dict:
        """طلب رقم جديد"""
        params = {
            'action': 'getNumber',
            'service': service,
            'forward': forward
        }
        if country is not None:
            params['country'] = country
        if operator:
            params['operator'] = operator
        if ref:
            params['ref'] = ref
            
        return self._request(params, 'POST', get_number=1)

    def set_status(self, id: str, status: int, forward: int = 0) -> Dict:
        """تعيين حالة التفعيل"""
        params = {
            'action': 'setStatus',
            'id': id,
            'status': status
        }
        if forward:
            params['forward'] = forward
            
        return self._request(params, 'POST', get_number=3)

    def get_status(self, id: str) -> Dict:
        """الحصول على حالة التفعيل"""
        return self._request({'action': 'getStatus', 'id': id}, get_number=2)

    def get_countries(self) -> Dict:
        """الحصول على قائمة الدول"""
        return self._request({'action': 'getCountries'}, parse_json=True)

    def get_prices(self, country: Optional[int] = None, service: Optional[str] = None) -> Dict:
        """الحصول على الأسعار"""
        params = {'action': 'getPrices'}
        if country is not None:
            params['country'] = country
        if service:
            params['service'] = service
            
        return self._request(params, parse_json=True)

# إنشاء كائن عام للاستخدام
API_KEY = "your_api_key_here"  # سيتم تعيينه من البيئة
sms_api = SMSActivate(API_KEY)
