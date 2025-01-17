import niquests
import json
import sys
import platform

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


http_proxy = config["binance"]["proxy"]["http"]
https_proxy = config["binance"]["proxy"]["https"]

proxies = {
    "http": http_proxy,
    "https": https_proxy,
}
url = "https://api.binance.com/api/v3/exchangeInfo"

r = niquests.get(url, proxies=proxies)
print(r)
print(r.text[0:1000])
