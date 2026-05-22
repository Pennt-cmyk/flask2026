from flask import Flask, render_template, request
from datetime import datetime
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

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
line_bot_api = LineBotApi('Tu14RHAD512d5pjRO3/88iHi1/LPerKPnnFW+CuQqtReNpiXhN9rPANaamAJmDLBc2ap3h3QS5uId2UADzY+DQ1JNiAuKe/E8G4bTb8irlQBUcQ90NOFgb35rnKd4S2LmzRYtrmnmBJ/naPRHPw63QdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('d9ac686c00ecef9aa09dedd0f9e5b776')

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
    return link

# 接收 LINE 訊息的路由
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 處理 LINE 對話邏輯：從 Firestore 抓資料
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text  # 讀取使用者傳來的文字 (例如："限制級")
    
    # 如果使用者點擊圖文選單傳送「我要看電影」
    if user_message == "我要看電影":
        reply_text = "您要查詢哪種分級的電影？ (例如：限制級、輔導級、普遍級)"
        
    # 如果使用者輸入了包含「級」的字，我們就去資料庫找
    elif "級" in user_message:
        db = firestore.client()
        collection_ref = db.collection("本週新片含分級")  # 這是你截圖裡用的集合名稱
        docs = collection_ref.get()
        
        info = ""
        for doc in docs:
            doc_data = doc.to_dict()
            
            # 【重要】這裡假設你資料庫裡記錄分級的欄位叫做 "rate"
            # 如果你的欄位名稱不同 (例如叫 "分級" 或 "class")，請把下面的 "rate" 改掉
            movie_rate = doc_data.get("rate", "") 
            
            # 如果使用者輸入的字 (例如 限制級) 有在這個電影的分級裡面
            if user_message in movie_rate:
                title = doc_data.get("title", "未知片名")
                hyperlink = doc_data.get("hyperlink", "無連結")
                
                # LINE 的換行是 \n，不是網頁的 <br>
                info += f"片名：{title}\n介紹：{hyperlink}\n\n"
        
        if info == "":
            reply_text = f"抱歉，資料庫裡面目前沒有 {user_message} 的電影喔！"
        else:
            reply_text = f"我是林珮芹開發的電影聊天機器人，您選擇的電影分級是 {user_message}，相關電影：\n\n{info}"
            
    else:
        reply_text = "我不太懂您的意思，請點擊選單或輸入電影分級。"

    # 將組合好的文字回傳給使用者
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )


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
            Result += str(teacher) + "<br>"  
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
