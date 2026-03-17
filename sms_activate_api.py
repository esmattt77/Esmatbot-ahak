import requests

class HeroSMSAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://hero-sms.com/stubs/handler_api.php"

    def _get(self, action, params=None):
        query_params = {'api_key': self.api_key, 'action': action}
        if params:
            query_params.update(params)
        try:
            response = requests.get(self.url, params=query_params)
            return response.text
        except Exception as e:
            return f"ERROR:{str(e)}"

    def get_balance(self):
        res = self._get('getBalance')
        if "ACCESS_BALANCE" in res:
            return res.split(":")[1]
        return "0"

    def get_number(self, service, country=0):
        res = self._get('getNumber', {'service': service, 'country': country})
        if "ACCESS_NUMBER" in res:
            parts = res.split(":")
            return {"id": parts[1], "number": parts[2]}
        return res

    def set_status(self, activation_id, status):
        # status: 1 (ready), 6 (complete), 8 (cancel)
        return self._get('setStatus', {'id': activation_id, 'status': status})

    def get_status(self, activation_id):
        return self._get('getStatus', {'id': activation_id})
