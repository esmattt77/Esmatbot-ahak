import requests
import json

class HeroSMSAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://hero-sms.com/stubs/handler_api.php"

    def _call(self, action, params=None):
        p = {'api_key': self.api_key, 'action': action}
        if params: p.update(params)
        try:
            r = requests.get(self.url, params=p, timeout=25)
            return r.text
        except: return "ERROR_CONNECTION"

    def get_balance(self):
        res = self._call('getBalance')
        return res.split(":")[1] if "ACCESS_BALANCE" in res else "0"

    def get_number(self, service, country=0):
        # طلب الرقم بنظام V2 للحصول على JSON كامل
        res = self._call('getNumberV2', {'service': service, 'country': country})
        try: return json.loads(res)
        except: return res

    def get_prices(self, service=None, country=None):
        params = {}
        if service: params['service'] = service
        if country: params['country'] = country
        res = self._call('getPrices', params)
        try: return json.loads(res)
        except: return {}

    def get_history(self):
        res = self._call('getHistory')
        try: return json.loads(res)
        except: return []

    def get_services_list(self):
        res = self._call('getServicesList', {'lang': 'en'})
        try: return json.loads(res)
        except: return {}

    def get_top_countries(self, service):
        res = self._call('getTopCountriesByService', {'service': service})
        try: return json.loads(res)
        except: return []

    def set_status(self, aid, status):
        return self._call('setStatus', {'id': aid, 'status': status})

    def get_status(self, aid):
        return self._call('getStatus', {'id': aid})
        
