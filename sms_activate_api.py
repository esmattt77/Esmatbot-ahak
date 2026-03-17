import requests
import json

class HeroSMSAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://hero-sms.com/stubs/handler_api.php"

    def _get(self, action, params=None):
        query_params = {'api_key': self.api_key, 'action': action}
        if params: query_params.update(params)
        try:
            response = requests.get(self.url, params=query_params, timeout=20)
            return response.text
        except: return "ERROR"

    def get_balance(self):
        res = self._get('getBalance')
        return res.split(":")[1] if "ACCESS_BALANCE" in res else "0"

    def get_number(self, service, country=0):
        # استخدام getNumberV2 للحصول على بيانات JSON أدق كما في التوثيق
        res = self._get('getNumberV2', {'service': service, 'country': country})
        try:
            return json.loads(res)
        except:
            # fallback للنظام القديم إذا فشل JSON
            return res

    def get_prices(self, service):
        res = self._get('getPrices', {'service': service})
        try:
            data = json.loads(res)
            # التوثيق يظهر أن الرد قد يكون مصفوفة [ { "service": { "cost": x } } ]
            # أو قاموس { "country": { "service": { "cost": x } } }
            return data
        except: return {}

    def set_status(self, activation_id, status):
        # 6 للإنهاء، 8 للإلغاء
        return self._get('setStatus', {'id': activation_id, 'status': status})

    def get_status(self, activation_id):
        return self._get('getStatus', {'id': activation_id})
        
