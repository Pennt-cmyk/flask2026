from flask import Flask, render_template, request, make_response, jsonify
from datetime import datetime
from google import genai
from google.genai import types

import os
import json
import requests
import firebase_admin
from firebase_admin import credentials, firestore

# 判斷是在 Vercel 還是本地
if os.path.exists('serviceAccountKey.json'):
    # 本地環境：讀取檔案
    cred = credentials.Certificate('serviceAccountKey.json')
else:
    # 雲端環境：從環境變數讀取 JSON 字串
    firebase_config = os.getenv('FIREBASE_CONFIG')
    cred_dict = json.loads(firebase_config)
    cred = credentials.Certificate(cred_dict)

firebase_admin.initialize_app(cred)


app = Flask(__name__)

client = genai.Client()


@app.route("/")
def index():
    link = "<h1>歡迎進入林珮芹的網站</h1>"
    link += "<a href=/mis>課程</a><hr>"
    link += "<a href=/today>現在日期時間</a><hr>"
    link += "<a href=/me>關於我</a><hr>"
    link += "<a href=/welcome?u=珮芹&d=靜宜資管&c=資訊管理導論>Get傳值</a><hr>"
    link += "<a href=/account>網頁表單傳值</a><hr>"
    link += "<a href=/penny>次方與根號計算</a><hr>"
    link += "<br><a href=/read>讀取Firestore資料</a><hr>"
    link += "<br><a href=/read2>讀取Firestore資料(根據姓名關鍵字:楊)</a><hr>"
    link += "<br><a href=/spider>爬取資料</a><hr>"
    link += "<br><a href=/movie1>爬取即將上映電影</a><hr>"
    link += "<br><a href=/mo>近期即將上映電影</a><hr>"
    link += "<br><a href=/searchMovie>搜尋近期即將上映電影</a><hr>"
    link += "<br><a href=/road>台中市十大肇事路口</a><hr>"
    link += "<br><a href=/weather>天氣</a><hr>"
    link += "<br><a href=/rate>本週新片</a><hr>"
    link += "<br><a href=/ask>詢問</a><hr>"
    link += "<br><a href=/messenger>詢問AI小視窗</a><hr>"
    return link

@app.route('/ask', methods=['GET', 'POST']) 
def ask():
    if request.method == "POST":
        user_prompt = request.form.get('prompt', '')
        if not user_prompt:
            return "請輸入內容", 400
        try:
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=user_prompt,
            )
            return response.text
        except Exception as e:
            return f"發生錯誤: {str(e)}", 500

    else:    
        # 當使用者直接打開網頁 (GET) 時，顯示輸入框畫面
        return render_template("ask.html")


@app.route("/AI")
def AI():
    # 每次使用者拜訪該路徑時，直接使用全域的 client 呼叫模型
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents='我想查詢靜宜大學資管系的評價？',
    )

    return response.text


@app.route("/webhook", methods=["POST"])
def webhook():
    # 建立 request 物件
    req = request.get_json(force=True)
    
    # 從 JSON 中取得 action，使用 .get() 避免報錯
    action = req.get("queryResult", {}).get("action", "")
    
    # 設定預設的回應，避免 action 都不符合時 info 未定義
    info = "抱歉，系統目前無法辨識您的指令。" 

    # --- 動作 1: 電影分級查詢 ---
    if action == "rateChoice":
        # 取得分級參數
        rate = req["queryResult"]["parameters"]["rate"]
        info = "我是林珮芹設計的機器人,您選擇的電影分級是：" + rate + "\n\n"
        
        # 資料庫查詢 (必須縮排在 if 區塊內)
        db = firestore.client()
        # 注意：這裡要改成你截圖中真實的集合名稱
        collection_ref = db.collection("本週新片含分級")
        docs = collection_ref.get()
        
        result = ""
        # 迴圈讀取每一筆電影資料
        for doc in docs:
            doc_dict = doc.to_dict()
            # 確認字典裡有 'rate' 且符合使用者選擇
            if "rate" in doc_dict and rate in doc_dict["rate"]:
                result += "片名：" + doc_dict["title"] + "\n"
                result += "介紹：" + doc_dict["hyperlink"] + "\n\n"
        
        # 判斷是否有找到資料
        if result == "":
            info += "抱歉，目前資料庫中沒有找到這個分級的電影喔！"
        else:
            info += result

    # --- 動作 2: 處理未知的輸入 (呼叫 Gemini API) ---
    elif action == "input.unknown":
        instruction_text = (
            "你是一個熱心且知識豐富的專業智慧助理。"
            "請用繁體中文、自然且完整的句子來回答使用者的問題，長度控制在 50 到 100 字左右。"         
        )

        ai_config = types.GenerateContentConfig(
            max_output_tokens=500, 
            system_instruction=instruction_text
        )
        
        try:
            # 注意：請確認 'gemini-3.5-flash' 是您實際要使用的正確模型名稱
            response = client.models.generate_content(
                model='gemini-3.5-flash', 
                contents=req["queryResult"]["queryText"],
                config=ai_config,
            )

            if response.text:
                info = response.text
            else:
                info = "抱歉，我現在無法生成回應，請稍後再試。"
        
        except Exception as e:
            # 捕捉並印出 API 錯誤，避免伺服器直接 500 報錯
            print(f"Gemini API 發生錯誤: {e}")
            info = "抱歉，AI 助理目前連線異常，請稍後再試。"

    # 回傳 JSON 格式給 Dialogflow
    return make_response(jsonify({"fulfillmentText": info}))


@app.route("/rate")
def rate():
    #本週新片
    url = "https://www.atmovies.com.tw/movie/new/"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    lastUpdate = sp.find(class_="smaller09").text[5:]
    print(lastUpdate)
    print()

    result=sp.select(".filmList")

    for x in result:
        title = x.find("a").text
        introduce = x.find("p").text

        movie_id = x.find("a").get("href").replace("/", "").replace("movie", "")
        hyperlink = "http://www.atmovies.com.tw/movie/" + movie_id
        picture = "https://www.atmovies.com.tw/photo101/" + movie_id + "/pm_" + movie_id + ".jpg"

        r = x.find(class_="runtime").find("img")
        rate = ""
        if r != None:
            rr = r.get("src").replace("/images/cer_", "").replace(".gif", "")
            if rr == "G":
                rate = "普遍級"
            elif rr == "P":
                rate = "保護級"
            elif rr == "F2":
                rate = "輔12級"
            elif rr == "F5":
                rate = "輔15級"
            else:
                rate = "限制級"

        t = x.find(class_="runtime").text

        t1 = t.find("片長")
        t2 = t.find("分")
        showLength = t[t1+3:t2]

        t1 = t.find("上映日期")
        t2 = t.find("上映廳數")
        showDate = t[t1+5:t2-8]

        doc = {
            "title": title,
            "introduce": introduce,
            "picture": picture,
            "hyperlink": hyperlink,
            "showDate": showDate,
            "showLength": int(showLength),
            "rate": rate,
            "lastUpdate": lastUpdate
        }

        db = firestore.client()
        doc_ref = db.collection("本週新片含分級").document(movie_id)
        doc_ref.set(doc)
    return "本週新片已爬蟲及存檔完畢，網站最近更新日期為：" + lastUpdate


@app.route("/weather")
def weather():
    # 1. 取得使用者在網頁網址或表單輸入的縣市
    # 這取代了原本的 city = input("請輸入縣市：")
    city = request.args.get("city")

    # 2. 如果使用者還沒有輸入，就先顯示一個網頁表單給他填寫
    if not city:
        return '''
            <h2>氣象查詢系統</h2>
            <form action="/weather" method="GET">
                請輸入縣市 (例如：臺中市)：<input type="text" name="city" required>
                <input type="submit" value="查詢">
            </form>
        '''

    # 3. 處理字串 (台換成臺)
    city_formatted = city.replace("台", "臺")
    
    # 4. 組合 API 網址 (已修正你原本程式碼中重複組合的問題)
    token = "rdec-key-123-45678-011121314"
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={token}&format=JSON&locationName={city_formatted}"
    
    # 為了避免你之前一直遇到的 10054 連線被阻擋問題，務必加上偽裝標頭
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
    }

    try:
        # 發送請求，記得加上 verify=False
        Data = requests.get(url, headers=headers, verify=False, timeout=10)
        
        if Data.status_code == 200:
            json_data = json.loads(Data.text)
            
            # 依照你原本的邏輯，挖出天氣與降雨機率
            # 這裡包在 try 裡面是為了避免使用者輸入錯的縣市名稱（例如：台中縣）導致 JSON 找不到該路徑
            try:
                location_data = json_data["records"]["location"][0]
                weather_status = location_data["weatherElement"][0]["time"][0]["parameter"]["parameterName"]
                rain_prob = location_data["weatherElement"][1]["time"][0]["parameter"]["parameterName"]
                
                # 回傳結果加上簡單的 HTML 排版
                return f'''
                    <h2>查詢結果：{city_formatted}</h2>
                    <p>目前天氣：{weather_status}</p>
                    <p>降雨機率：{rain_prob}%</p>
                    <br><br>
                    <a href="/weather">返回重新查詢</a>
                '''
            except IndexError:
                return f"找不到「{city}」的資料，請確認縣市名稱是否輸入正確（如：臺中市）。<br><a href='/weather'>返回重新查詢</a>"
                
        else:
            return f"無法取得資料，錯誤代碼：{Data.status_code}"

    except Exception as e:
        return f"連線發生錯誤：{e}"


@app.route("/road")
def road():
    R = "<h1>台中市十大肇事路口(113年10月)作者:林珮芹</h1><br>"
    url = "https://datacenter.taichung.gov.tw/swagger/OpenData/a1b899c0-511f-4e3d-b22b-814982a97e41"
    
    # 關鍵：加上這段偽裝標頭，讓伺服器以為你是瀏覽器
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # 同時包含 headers 和 verify=False
        Data = requests.get(url, headers=headers, verify=False, timeout=10)
        
        if Data.status_code == 200:
            JsonData = json.loads(Data.text)
            for item in JsonData:
                R += f"{item['路口名稱']}，原因：{item['主要肇因']}: 發生 {item['總件數']}件<br>"
        else:
            R += f"無法取得資料，錯誤代碼：{Data.status_code}"
            
    except Exception as e:
        R += f"連線發生錯誤：{e}"
        
    return R


@app.route("/searchMovie", methods=["POST", "GET"])
def searchMovie():
    if request.method == "POST":
        MovieTitle = request.form["MovieTitle"]
        info = ""
        
        db = firestore.client()
        collection_ref = db.collection("電影2B")
        docs = collection_ref.order_by("showDate").get()
        
        for doc in docs:
            if MovieTitle in doc.to_dict()["title"]:
                info += "編號：" + doc.id + "<br>"  # 使用 doc.id 取得 Firestore 的文件編號
                info += "片名：" + doc.to_dict()["title"] + "<br>"
                info += "海報：<img src='" + doc.to_dict()["picture"] + "' width='200'><br>"
                info += "介紹頁：<a href='" + doc.to_dict()["hyperlink"] + "'>" + doc.to_dict()["hyperlink"] + "</a><br>"
                info += "上映日期：" + doc.to_dict()["showDate"] + "<br><br>"
        
        if info == "":
            info = "資料庫中找不到符合此關鍵字的電影。"
            
        return info
    else:
        return render_template("input.html")

@app.route("/messenger")
def messenger():
    return render_template("messenger.html")

@app.route("/mo")
def mo():
    R = ""
    db = firestore.client()


    import requests
    from bs4 import BeautifulSoup
    url = "http://www.atmovies.com.tw/movie/next/"
    Data = requests.get(url)
    Data.encoding = "utf-8"

    sp = BeautifulSoup(Data.text, "html.parser")
    lastUpdate = sp.find(class_="smaller09").text.replace("更新時間：","")

    result=sp.select(".filmListAllX li")
    info = ""
    total = 0
    for item in result:
      total += 1
      movie_id = item.find("a").get("href").replace("/movie/","").replace("/","")
      title = item.find(class_="filmtitle").text
      picture =  "https://www.atmovies.com.tw" + item.find("img").get("src")
      hyperlink =  "https://www.atmovies.com.tw" + item.find("a").get("href")

      showDate = item.find(class_="runtime").text[5:15]
      info += movie_id + "\n" + title + "\n" 
      info += picture + "\n" + hyperlink + "\n" + showDate +  "\n\n"


      doc = {
          "title": title,
          "picture": picture,
          "hyperlink": hyperlink,
          "showDate": showDate,
          "lastUpdate": lastUpdate
      }

      doc_ref = db.collection("電影2B").document(movie_id)
      doc_ref.set(doc)

    R += "網站最近更新日期:" + lastUpdate + "<br>"
    R += "總共爬取" + str(total) + "部電影到資料庫"           

    return R

@app.route("/movie1")
def movie1():
    keyword = request.args.get("keyword", "")
    

    R = """
    <form action="/movie1" method="get">
        <label>請輸入電影關鍵字：</label>
        <input type="text" name="keyword" value="{}">
        <button type="submit">搜尋</button>
    </form>
    <hr>
    """.format(keyword) 
    
    if keyword:
        R += "您搜尋的關鍵字是：<b>" + keyword + "</b><br><br>"
    
    url = "https://www.atmovies.com.tw/movie/next/"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    result = sp.select(".filmListAllX li")
    
    for item in result:
        title = item.find("img").get("alt")
        
        if not keyword or keyword in title:
            introduce = "https://www.atmovies.com.tw" + item.find("a").get("href")
            img_url = "https://www.atmovies.com.tw" + item.find("img").get("src")
            
            R += "<b>" + title + "</b><br>"
            R += '<a href="' + introduce + '" target="_blank">介紹頁超鏈結</a><br>'
            R += '<img src="' + img_url + '" width="200"><br><br>'
            
    return R

import requests
from bs4 import BeautifulSoup
from flask import Flask

# ... 你的 app 定義 ...

@app.route("/spider")
def spider():
    final_output = "" 
    url = "https://www1.pu.edu.tw/~tcyang/course.html"
    
    try:
        requests.packages.urllib3.disable_warnings()
        response = requests.get(url, verify=False)
        response.encoding = "utf-8" # 確保中文不會變成亂碼

        soup = BeautifulSoup(response.text, "html.parser")
        
        # 3. 選取目標：根據你的 CSS 選擇器找出所有連結
        links = soup.select(".team-box a")
        
        # 4. 迴圈整理資料
        for item in links:
            text = item.text.strip() # 取得文字並去掉空格
            href = item.get("href")  # 取得連結
            # 使用 + 號連接字串，並加上 <br> 讓網頁換行
            final_output += f"項目：{text} | 連結：{href}<br>"
            
        # 如果沒抓到東西，給個提示
        if not final_output:
            final_output = "已連線，但找不到指定的 CSS 標籤 (.team-box a)"
            
    except Exception as e:
        # 萬一發生其他錯誤（例如斷網），會顯示在網頁上方便除錯
        final_output = f"發生錯誤：{str(e)}"
        
    return final_output


@app.route("/read1")
def read1():
    Result = ""
    keyword = "楊"
    db = firestore.client()
    collection_ref = db.collection("靜宜資管")    
    docs = collection_ref.get()    
    for doc in docs:
        teacher = doc.to_dict()
        if keyword in teacher["name"]:         
            Result += str( teacher) + "<br>"  
    return Result


@app.route("/read")
def read():
    Result = ""
    db = firestore.client()
    collection_ref = db.collection("靜宜資管")    
    docs = collection_ref.get()    
    for doc in docs:         
        Result += str(doc.to_dict()) + "<br>"  
    return Result


@app.route("/mis")
def course():
    return "<h1>資訊管理導論</h1><a href=/>返回首頁</a>"

@app.route("/today")
def today():
    now = datetime.now()
    return render_template("today.html", datetime = str(now))

@app.route("/me")
def me():
    return render_template("01.html")

@app.route("/welcome", methods=["GET"])
def welcome():
    user = request.values.get("u")
    d = request.values.get("d")
    c = request.values.get("c")
    return render_template("welcome.html", name = user,dep = d,course =c)

@app.route("/account", methods=["GET", "POST"])
def account():
    if request.method == "POST":
        user = request.form["user"]
        pwd = request.form["pwd"]
        result = "您輸入的帳號是：" + user + "; 密碼為：" + pwd 
        return result
    else:
        return render_template("account.html")

@app.route("/read2", methods=["GET", "POST"])
def read2():
    # 網頁標題與查詢表單
    Result = "<h1>靜宜資管老師查詢</h1>"
    Result += '<form action="/read2" method="post">'
    Result += '請輸入老師姓名關鍵字：<input type="text" name="keyword">'
    Result += '<button type="submit">查詢</button></form><br>'

    if request.method == "POST":
        keyword = request.form.get("keyword")
        Result += f"<h3>查詢結果 (關鍵字: {keyword}):</h3>"
       
        db = firestore.client()
        collection_ref = db.collection("靜宜資管")
        docs = collection_ref.get()
       
        found = False
        for doc in docs:
            teacher_data = doc.to_dict()
            name = teacher_data.get('name')
           

            if name and keyword in name:
                found = True
                lab = teacher_data.get('lab', '未知')
                Result += f"<span style='color:blue; font-weight:bold'>{name}</span> 老師的研究室是在 <b>{lab}</b><br>"
       
        if not found:
            Result += f"找不到姓名包含「{keyword}」的老師。<br>"

    Result += "<br><a href=/>返回首頁</a>"
    return Result


@app.route("/penny")
def penny():
    return render_template("02.html")


if __name__ == "__main__":
    app.run(debug=True)
