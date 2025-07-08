from flask import Flask, render_template, request, redirect, jsonify
import json
import os
from datetime import datetime
import pytz
import requests 

app = Flask(__name__)
DATA_DIR = "data"
BOOTH_FILE = os.path.join(DATA_DIR, "booths.json")
NOTIFY_FILE = os.path.join(DATA_DIR, "notifications.json")


def load_booths():
    with open(BOOTH_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_booths(data):
    with open(BOOTH_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_notifications():
    with open(NOTIFY_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_notifications(data):
    with open(NOTIFY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.route("/")
def index():
    booths = load_booths()
    notifs = load_notifications()
    return render_template("index.html", booths=booths, notifications=notifs)


@app.route("/admin")
def admin():
    booths = load_booths()
    return render_template("admin.html", booths=booths)


@app.route("/admin/<class_id>")
def admin_class(class_id):
    booths = load_booths()
    target = next((b for b in booths if b["class"] == class_id), None)

    if target:
        booth_name = target.get("booth_name", "")
        history = target.get("history", [])
        latest_status = history[-1]["status"] if history else 1  # デフォルト1=空
    else:
        booth_name = ""
        latest_status = 1

    return render_template(
        "admin.html",
        class_id=class_id,
        booth_name=booth_name,
        status=latest_status,
        booths=booths
    )



@app.route("/api/update_status", methods=["POST"])
def api_update_status():
    data = request.get_json()
    cls = data["class"]
    booth_name = data["booth_name"]
    status = int(data["status"])
    now = datetime.now(pytz.timezone("Asia/Tokyo")).strftime("%H:%M")

    booths = load_booths()
    for booth in booths:
        if booth["class"] == cls:
            booth["booth_name"] = booth_name
            booth.setdefault("history", []).append({ "time": now, "status": status })
            break
    else:
        booths.append({
            "class": cls,
            "booth_name": booth_name,
            "history": [ { "time": now, "status": status } ]
        })

    save_booths(booths)
    return jsonify(success=True)




@app.route("/notify", methods=["GET", "POST"])
def notify():
    if request.method == "POST":
        caller = request.form["caller"]
        msg = request.form["message"]
        notifs = load_notifications()
        #追加します（ハオ）
        now_time = datetime.now(pytz.timezone("Asia/Tokyo")).strftime("%H:%M")
        #ここまで
        notifs.insert(0, {
            "time": datetime.now(pytz.timezone("Asia/Tokyo")).strftime("%H:%M"),
            "message": f"{msg} ({caller})"
        })
        save_notifications(notifs)

        #はおpowerAutomate
        url = "https://prod-59.japaneast.logic.azure.com:443/workflows/45e0342f8f3f48208cef4d400691a440/triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=W5IT3euqOf2L9jMLyeJs4cG9sJCUrbVZZZ5vwA5S3Bg"
        payload = {
            "caller":caller,
            "message":f"{msg}"
        }
        try:
            requests.post(url,json=payload)
        except Exception as e:
            print("Teamsに送れませんでした:",e)
        #ここまで
        return redirect("/notify")
    notifs = load_notifications()
    return render_template("notify.html", notifications=notifs)

#HTML側
@app.route("/api/booths")
def api_booths():
    booths = load_booths()
    for booth in booths:
        if "history" in booth and booth["history"]:
            booth["status"] = booth["history"][-1]["status"]
    return jsonify(booths)

@app.route("/api/status_history/<class_id>")
def api_status_history_class(class_id):
    booths = load_booths()
    for booth in booths:
        if booth["class"] == class_id:
            return jsonify({
                "class": booth["class"],
                "booth_name": booth["booth_name"],
                "history": booth.get("history", [])
            })
    return jsonify({"error": "クラスが見つかりません"}), 404

@app.route("/api/notifications")
def api_notifications():
    return jsonify(load_notifications())

@app.route("/delete_notification", methods=["POST"])
def delete_notification():
    time = request.form["time"]
    message = request.form["message"]
    notifications = load_notifications()
    notifications = [n for n in notifications if not (n["time"] == time and n["message"] == message)]
    save_notifications(notifications)
    return redirect("/notify")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)