import requests
import json
import urllib3

# --- 新增這兩行來解決出不來的問題 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# ------------------------------

url = "https://datacenter.taichung.gov.tw/swagger/OpenData/a1b899c0-511f-4e3d-b22b-814982a97e41"

# 在 requests.get 裡面加上 verify=False
Data = requests.get(url, verify=False)

JsonData = json.loads(Data.text)
Result = ""

for item in JsonData:
    # 這裡完全依照老師投影片的格式
    Result += item["路口名稱"] + "：發生" + str(item["總件數"]) + "件，主因是" + item["主要肇因"] + "\n"

print(Result)