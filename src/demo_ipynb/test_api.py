import niquests
import json
import sys

if sys.platform.startswith("linux"):
    print("Linux")
    file_path = "/root/chameleon-quant/strategy/config.json"
elif sys.platform.startswith("win"):
    file_path = "src/strategy/config.json"
    print("Windows")
elif sys.platform.startswith("darwin"):
    print("macOS")
else:
    print("Unsatisfactory")


with open(file_path, "r", encoding="utf-8") as file:
    config = json.load(file)


http_proxy = config["binance"]["proxy"].get("http", None)
https_proxy = config["binance"]["proxy"].get("https", None)

proxies = {
    "http": http_proxy,
    "https": https_proxy,
}

api = "https://api.binance.com"


def get_url(api):
    return f"{api}/api/v3/exchangeInfo"


url = get_url(api)

r = niquests.get(url, proxies=proxies)
print(r)
print(r.text[0:1000])
