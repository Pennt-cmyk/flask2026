import requests
from bs4 import BeautifulSoup

url = "https://www1.pu.edu.tw/~tcyang/course.html"
Data = requests.get(url, verify=False)
Data.encoding = "utf-8"
sp = BeautifulSoup(Data.text,"html.parser")
result = sp.select(".team-box a")

all_data = ""

for i in result:
    title = i.text.strip()
    link = i.get("href")    
    if title and link:
        all_data += title + " " + link + "<br>"
print(all_data.replace("<br>", "\n"))