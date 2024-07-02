import base64
import requests
from requests.exceptions import JSONDecodeError, Timeout
from urllib.parse import unquote, quote

# ref https://github.com/gyje/tplink_encrypt/blob/9d93c2853169038e25f4e99ba6c4c7b833d5957f/tpencrypt.py
def tp_encrypt(password):

    a = 'RDpbLfCPsJZ7fiv'
    c = 'yLwVl0zKqws7LgKPRQ84Mdt708T1qQ3Ha7xv3H7NyU84p21BriUWBU43odz3iP4rBL3cD02KZciXTysVXiV8ngg6vL48rPJyAUw0HurW20xqxv9aYb4M9wK1Ae0wlro510qXeU07kV57fQMc8L6aLgMLwygtc0F10a0Dg70TOoouyFhdysuRMO51yY5ZlOZZLEal1h0t9YQW0Ko7oBwmCAHoic4HYbUyVeU3sfQ1xtXcPcf1aT303wAQhv66qzW'
    b = password
    e = ''
    f, g, h, k, l = 187, 187, 187, 187, 187
    n = 187
    g = len(a)
    h = len(b)
    k = len(c)
    if g > h:
        f = g
    else:
        f = h
    for p in list(range(0, f)):
        n = l = 187
        if p >= g:
            n = ord(b[p])
        else:
            if p >= h:
                l = ord(a[p])
            else:
                l = ord(a[p])
                n = ord(b[p])
        e += c[(l ^ n) % k]
    return e


# # ref https://www.cnblogs.com/masako/p/7660418.html
def convert_rsa_key(s):
    b_str = base64.b64decode(s)
    if len(b_str) < 162:
        return False
    hex_str = b_str.hex()
    m_start = 29 * 2
    e_start = 159 * 2
    m_len = 128 * 2
    e_len = 3 * 2
    modulus = hex_str[m_start:m_start + m_len]
    exponent = hex_str[e_start:e_start + e_len]
    return modulus, exponent

def rsa_encrypt(string, pubkey):
    # from Crypto.PublicKey import RSA
    # from Crypto.Cipher import PKCS1_v1_5 as Cipher_PKCS1_v1_5
    # from base64 import b64decode,b64encode

    # print(pubkey)
    # keyDER = b64decode(pubkey)
    # keyPub = RSA.importKey(keyDER)
    # cipher = Cipher_PKCS1_v1_5.new(keyPub)
    # cipher_text = cipher.encrypt(string.encode())
    # emsg = b64encode(cipher_text)
    # return emsg

    print(pubkey)
    import rsa
    key = convert_rsa_key(pubkey)
    if not key:
        raise ValueError("Invalid RSA key")
    modulus = int(key[0], 16)
    exponent = int(key[1], 16)
    rsa_pubkey = rsa.PublicKey(modulus, exponent)
    crypto = rsa.encrypt(string.encode(), rsa_pubkey)
    return base64.b64encode(crypto)

class TPLinkIPCamError(Exception): pass
class AuthenticationError(TPLinkIPCamError): pass
class ServerError(TPLinkIPCamError): pass
class InvalidResponseError(TPLinkIPCamError): pass
class ConnectionError(TPLinkIPCamError): pass
class APIError(TPLinkIPCamError): pass

def format_response(response: requests.Response):
    return f"{response.status_code} - {response.reason} - {response.content.decode(errors='replace')[:1000]}"

class TPLinkIPCam44AW:
    def _get_url(url_base, stok=""):
        url_base = url_base.rstrip('/')
        if stok == "":
            return '{url_base}/'.format(url_base=url_base)
        else:
            return '{url_base}/stok={stok}/ds'.format(url_base=url_base, stok=stok)

    def _request_api(url, method, request_data, tolerate_401=False):
        return TPLinkIPCam44AW._request(url, {"method": method, **request_data}, tolerate_401)

    def _request(url, json_data, tolerate_401=False):
        try:
            if json_data is None:
                response = requests.get(url, timeout=10)
            else:
                response = requests.post(url, json=json_data, timeout=10)
        except Timeout:
            raise ConnectionError("Connection timed out")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(e)
        
        if response.status_code == 401:
            if not tolerate_401:
                raise AuthenticationError(format_response(response))
        elif response.status_code != 200:
            raise ServerError(format_response(response))

        try:
            result = response.json()
        except JSONDecodeError:
            raise InvalidResponseError(format_response(response))

        if "error_code" not in result:
            raise InvalidResponseError(format_response(response))

        error_code = result['error_code']
        if error_code == 0:
            return result
        elif error_code == -40401:
            if tolerate_401:
                return result
            raise AuthenticationError(format_response(response))
        else:
            raise APIError("Error: " + str(result))

    def __init__(self, url_base, username, password, rsa=False):
        url_base = url_base.rstrip('/')
        self.url_base = url_base
        self.username = username
        self.password = password
        self.rsa = rsa
        self.stok = ""
        self.is_logged_in = False
        self.collected_req = dict()
        self.info = dict()
        self.state = dict(
            mask_enabled=True
        )

    def login(self):
        self.stok = ""
        if self.rsa:
            # get key nonce
            # j = self.request("do", {"login": {}}, tolerate_401=True)
            j = TPLinkIPCam44AW._request("{url_base}/pc/Content.htm".format(url_base=self.url_base), None, tolerate_401=True)
            print(j)
            key = unquote(j['data']['key'])
            nonce = str(j['data']['nonce'])

            # encrypt tp
            password = self.password
            # password += ":" + nonce

            # rsa password
            rsa_password = rsa_encrypt(password, key)
            print(rsa_password)

            d = {
                "login": {
                    "username": self.username,
                    "encrypt_type": "2",
                    "password": quote(rsa_password)
                }
            }
        else:
            tp_password = tp_encrypt(self.password)
            d = {
                "login": {
                    "username": self.username,
                    "encrypt_type": "1",
                    "password": quote(tp_password)
                }
            }

        j = self.request("do", d)
        self.stok = j["stok"]
        if self.stok == "":
            raise AuthenticationError("No stok")
        self.is_logged_in = True

    def request(self, method, request_data, tolerate_401=False):
        return TPLinkIPCam44AW._request_api(TPLinkIPCam44AW._get_url(self.url_base, stok=self.stok), method, request_data, tolerate_401)

    def user_request(self, method, request_data):
        if self.stok == "":
            self.login()
        if self.stok == "":
            raise AuthenticationError("No stok")
        try:
            return self.request(method, request_data) 
        except AuthenticationError:
            self.login()
            return self.request(method, request_data)

    def collect_request(self, method, request_data):
        assert method in ["get"], "Only get method can be collected"
        assert isinstance(request_data, dict)
        if method not in self.collected_req:
            self.collected_req[method] = dict()

        merged_req = self.collected_req[method]
        for category, category_data in request_data.items():
            assert isinstance(category_data, dict) and len(category_data) == 1 and "name" in category_data
            if category not in merged_req:
                merged_req[category] = {"name": list()}

            category_names = category_data["name"]
            assert isinstance(category_names, str) or isinstance(category_names, list)
            if isinstance(category_names, str):
                category_names = [category_names]
            merged_req[category]["name"] = list(set(merged_req[category]["name"]).union(set(category_names)))

    def make_collected_request(self, method):
        if method not in self.collected_req:
            return
        collected = self.collected_req[method]
        self.collected_req[method].clear()
        return self.user_request(method, collected)
    
    def get_module_spec(self):
        return self.user_request("get", {"function":{"name": ['module_spec']}})

    def get_audio_spec(self):
        return self.user_request("get", {"audio_capability":{"name": ['device_speaker', 'device_microphone']}})

    def get_motor_capability(self): 
        return self.user_request("get", {"motor":{"name": ['capability']}})

    def get_vhttpd(self):
        return self.user_request("get", {"cet":{"name": ['vhttpd']}}) 

    def get_basic_info(self):
        return self.user_request("get", {"device_info":{"name": ['basic_info']}})

    def get_sdcard_info(self):
        return self.user_request("get", {"sd_manage":{"table": ['sd_info']}})

    def get_time(self):
        return self.user_request("get", {"system":{"name": ['clock_status']}})

    def motor_move(self, degree):
        result = self.user_request("do", {"motor":{"movestep":{"direction":degree}}})

    def set_mask(self, enabled):
        result = self.user_request("set", {"lens_mask":{"lens_mask_info":{"enabled": "on" if enabled else "off"}}})

    def get_mask(self):
        result = self.user_request("get", {"lens_mask":{"name": "lens_mask_info"}})
        return result["lens_mask"]["lens_mask_info"]["enabled"] == "on"

    def get_mac(self):
        result = self.get_basic_info()
        return result["device_info"]["basic_info"]["mac"]

    def update_info(self):
        basic_info = self.get_basic_info()["device_info"]["basic_info"]
        for item_key in basic_info.keys():
            if not isinstance(basic_info[item_key], str):
                continue
            basic_info[item_key] = unquote(basic_info[item_key])
        self.info.update(basic_info)

    def update(self):
        self.state["mask_enabled"] = self.get_mask()

    @property
    def is_mask_on(self) -> bool:
        return self.state["mask_enabled"]
