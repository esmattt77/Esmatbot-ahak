import requests
import json
import logging

logger = logging.getLogger(__name__)

# =================================================================
#               1. فئات معالجة الأخطاء (Error Handling)
# =================================================================

class RequestError(Exception):
    """استثناء مخصص لأخطاء API التي يتم إرجاعها كرسائل خطأ من sms-activate."""
    ERROR_CODES = {
        'ACCESS_ACTIVATION': 'الخدمة تم تفعيلها بنجاح',
        'ACCESS_CANCEL': 'تم إلغاء التفعيل',
        'ACCESS_READY': 'في انتظار رسالة نصية جديدة',
        'ACCESS_RETRY_GET': 'تم تأكيد جاهزية الرقم',
        'ACCOUNT_INACTIVE': 'لا يوجد أرقام متاحة',
        'ALREADY_FINISH': 'تم إنهاء الإيجار بالفعل',
        'ALREADY_CANCEL': 'تم إلغاء الإيجار بالفعل',
        'BAD_ACTION': 'إجراء غير صحيح (معلمة action)',
        'BAD_SERVICE': 'اسم خدمة غير صحيح (معلمة service)',
        'BAD_KEY': 'مفتاح API غير صحيح',
        'BAD_STATUS': 'محاولة تعيين حالة غير موجودة',
        'BANNED': 'تم حظر الحساب',
        'CANT_CANCEL': 'لا يمكن إلغاء الإيجار (مر أكثر من 20 دقيقة)',
        'ERROR_SQL': 'أحد المعلمات لديها قيمة غير صالحة',
        'NO_NUMBERS': 'لا يوجد أرقام متاحة لاستقبال الرسائل النصية لهذه الخدمة',
        'NO_BALANCE': 'لا يوجد رصيد كافٍ',
        'NO_CONNECTION': 'لا يوجد اتصال بخوادم sms-activate', # ⬅️ هذا هو الخطأ الذي ظهر لديك
        'NO_ID_RENT': 'لم يتم تحديد معرف الإيجار',
        'NO_ACTIVATION': 'معرف التفعيل المحدد غير موجود',
        'STATUS_CANCEL': 'تم إلغاء التفعيل/الإيجار',
        'STATUS_FINISH': 'تم الدفع مقابل الإيجار وإنهاؤه',
        'STATUS_WAIT_CODE': 'في انتظار الرسالة النصية الأولى',
        'STATUS_WAIT_RETRY': 'في انتظار توضيح الرمز',
        'SQL_ERROR': 'أحد المعلمات لديها قيمة غير صالحة',
        'INVALID_PHONE': 'الرقم ليس مستأجراً من قبلك',
        'INCORECT_STATUS': 'الحالة مفقودة أو غير صحيحة',
        'WRONG_SERVICE': 'الخدمة لا تدعم إعادة التوجيه',
        'WRONG_SECURITY': 'خطأ في الأمان'
    }

    def __init__(self, error_code: str):
        self.error_code = error_code
        message = self.ERROR_CODES.get(error_code, f"خطأ غير معروف من API: {error_code}")
        super().__init__(message)
    
    def get_api_error_message(self):
        return self.ERROR_CODES.get(self.error_code, self.error_code)

# =================================================================
#                 2. فئة واجهة برمجة التطبيقات (API Class)
# =================================================================

class SMSActivate:
    """واجهة Python لـ SMS-Activate API."""

    BASE_URL = 'https://api.sms-activate.org/stubs/handler_api.php'
    
    def __init__(self, api_key: str):
        self.api_key = api_key

    def _request(self, params: dict, is_json_response=False):
        """
        إجراء طلب HTTP إلى API والتحقق من الأخطاء.

        :param params: معلمات الطلب (action, service, id, etc.).
        :param is_json_response: توقع استجابة JSON بدلاً من استجابة نصية.
        :return: البيانات المحللة (قاموس أو قيمة نصية).
        :raises RequestError: إذا كان هناك خطأ معروف من API.
        :raises requests.exceptions.RequestException: لأخطاء الاتصال بالشبكة.
        """
        
        # إضافة مفتاح API لجميع الطلبات
        params['api_key'] = self.api_key
        
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status() # إثارة استثناء لأكواد الحالة HTTP غير الناجحة (4xx أو 5xx)
            
        except requests.exceptions.RequestException as e:
            # معالجة أخطاء الشبكة العامة (DNS, Timeout, Connection Refused)
            logger.error(f"فشل الاتصال بـ SMS-Activate API: {e}")
            raise RequestError('NO_CONNECTION')
        
        result_text = response.text.strip()
        
        # 1. التحقق من أخطاء API (مثل BAD_KEY, NO_BALANCE)
        if result_text in RequestError.ERROR_CODES:
             # إذا كان النص هو أحد أكواد الخطأ الثابتة
            raise RequestError(result_text)

        # 2. تحليل استجابة JSON (لـ getBalance, getPrices, getCountries)
        if is_json_response:
            try:
                # التحقق مما إذا كانت الاستجابة JSON وفيها حالة فشل
                data = response.json()
                if isinstance(data, dict) and data.get("status") == "error" and "message" in data:
                    # قد يعود بعض الأخطاء في JSON، سنحاول إثارةها كـ RequestError
                    error_msg = data['message']
                    if error_msg in RequestError.ERROR_CODES:
                        raise RequestError(error_msg)
                    else:
                        raise Exception(f"خطأ JSON غير معالج: {error_msg}")
                return data
            except json.JSONDecodeError:
                logger.warning(f"فشل فك تشفير JSON: {result_text}")
                # إذا فشل JSON، قد تكون رسالة خطأ نصية لم يتم التقاطها
                if result_text in RequestError.ERROR_CODES:
                    raise RequestError(result_text)
                raise Exception(f"استجابة غير صالحة: {result_text}")

        # 3. تحليل الاستجابة النصية القياسية (لـ getNumber, getStatus)
        return result_text

    # -----------------------------------------------------------------
    #                 طرق المستخدم (User Methods)
    # -----------------------------------------------------------------

    def get_balance_and_cashback(self) -> dict:
        """جلب الرصيد والرصيد النقدي (Cashback) للحساب."""
        params = {'action': 'getBalanceAndCashBack'}
        # الاستجابة القياسية هنا هي ACCESS_BALANCE:123.456, لكننا نستخدم الطريقة التي تدعم JSON
        # بالرجوع إلى التوثيق، getBalanceAndCashBack لا يعود بـ JSON في نمط handler_api.php
        # الاستجابة المتوقعة: ACCESS_BALANCE:123.456

        result = self._request(params)
        
        if result.startswith('ACCESS_BALANCE:'):
            parts = result.split(':')
            balance = float(parts[1])
            # لا يمكننا استخراج cashback من هذه الاستجابة، فقط الرصيد الإجمالي
            return {'balance': balance, 'cashback': 0.0} 
        else:
             raise Exception(f"صيغة رصيد غير متوقعة: {result}")


    def get_countries(self) -> dict:
        """جلب قائمة الدول (اسم، كود، إلخ)."""
        params = {'action': 'getCountries'}
        # التوثيق يظهر أن هذه الاستجابة تكون JSON
        return self._request(params, is_json_response=True)


    def get_prices(self, service: str) -> dict:
        """جلب الأسعار والكميات المتاحة لدولة وخدمة معينة."""
        params = {'action': 'getPrices', 'service': service}
        # التوثيق يظهر أن هذه الاستجابة تكون JSON
        # الشكل: {"Country":{"Service":{"cost":"Cost","count":"Quantity"}}}
        return self._request(params, is_json_response=True)


    def get_number(self, service: str, country: int = 0) -> dict:
        """طلب رقم جديد للخدمة والدولة المحددة."""
        params = {'action': 'getNumber', 'service': service, 'country': country}
        result = self._request(params)
        
        # الاستجابة المتوقعة: ACCESS_NUMBER:ID:PHONE
        if result.startswith('ACCESS_NUMBER:'):
            parts = result.split(':')
            return {'id': parts[1], 'number': parts[2]}
        else:
            raise Exception(f"صيغة رقم غير متوقعة: {result}")


    def set_status(self, id: str, status: int) -> str:
        """تغيير حالة التفعيل (مثل إلغاء أو إنهاء)."""
        params = {'action': 'setStatus', 'id': id, 'status': status}
        result = self._request(params)
        
        # الاستجابة المتوقعة: ACCESS_READY, ACCESS_ACTIVATION, STATUS_CANCEL, إلخ.
        if result in RequestError.ERROR_CODES:
            # هذه قد تكون رسالة نجاح وليست خطأ (مثل ACCESS_READY)
            return RequestError.ERROR_CODES[result]
        else:
            return result # إرجاع النص كما هو إذا لم يكن كود خطأ/نجاح معروف


    def get_status(self, id: str) -> dict:
        """التحقق من حالة التفعيل والكود (إذا وصل)."""
        params = {'action': 'getStatus', 'id': id}
        result = self._request(params)
        
        # الاستجابة المتوقعة: STATUS_OK:CODE أو STATUS_WAIT_CODE أو STATUS_CANCEL
        parts = result.split(':')
        status = parts[0]
        code = parts[1] if len(parts) > 1 else None
        
        # إذا كانت الحالة أحد رسائل الخطأ/النجاح المعروفة
        if status in RequestError.ERROR_CODES:
            return {'status': status, 'code': code}
        
        # إذا كانت صيغة غير متوقعة
        raise Exception(f"صيغة حالة غير متوقعة: {result}")

# تهيئة الكائن ليتم استيراده في bot.py
# يتم تعيين api_key لاحقاً في bot.py من متغيرات البيئة
sms_api = SMSActivate(api_key="") 
