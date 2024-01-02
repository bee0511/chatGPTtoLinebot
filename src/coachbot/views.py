from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent,
    TextSendMessage,
    StickerSendMessage,
)

import openai
import os
import json
from mylinebot.secret import OPENAI_API_KEY


line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY

init_finish = False
personal_info = {}
modify_plan = False
finish_plan = False


def getHistory(path):
    """Read the chat history from the history.json"""
    history = []
    # test file exist, if not exict, create one
    try:
        with open(path, "r") as f:
            history = json.loads(f.read())
    except:
        with open(path, "w") as f:
            f.write(json.dumps(history, ensure_ascii=False, indent=4))
    return history

def storeInfo(message, path):
    """Store the info like personal info and plan to the info.json and plan.json"""
    # append the message to the file
    try:
        with open(path, "r") as f:
            data = json.loads(f.read())
            data.append(message)
        with open(path, "w") as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=4))
    except:
        with open(path, "w") as f:
            f.write(json.dumps([message], ensure_ascii=False, indent=4))

def chat(message, history, path):
    history.append({"role": "user", "content": message + " 請用繁體中文回答"})
    response = openai.chat.completions.create(model="gpt-3.5-turbo", messages=history)
    response_message = response.choices[0].message
    history.append({"role": response_message.role, "content": response_message.content})
    with open(path, "w") as f:
        f.write(json.dumps(history, ensure_ascii=False, indent=4))
    return response_message.content


def linebot_chat(event, message):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=message),
    )


info_index = 0
info_keys = ["年齡", "性別", "身高(cm)", "體重(kg)", "預計一週運動次數", "預計總共一週運動時間(小時)", "目標", "目標計劃時間(週)", "目標計畫開始時間", "偏好運動方式"]


def init(event):
    global info_index
    global init_finish
    if info_index < len(info_keys):
        if info_index > 0:
            personal_info[info_keys[info_index - 1]] = event.message.text
        message = "請問你的" + info_keys[info_index] + "是? "
        if info_index == 4:
            message += "(建議每週3-5次)"
        if info_index == 5:
            message += " (建議每週3小時以上)"
        if info_index == 6:
            message += "(例如:減重、增肌、維持)"
        if info_index == 7:
            message += "(例如:3週、4週、5週)"
        if info_index == 8:
            message += "(例如:2024/1/1)"
        if info_index == 9:
            message += "(例如:慢跑10公里, 游泳1小時, 腿部訓練1小時...)"
        linebot_chat(event, message=message)
        info_index += 1
    elif event.message.text == "@confirm":
        user_id = event.source.user_id
        path = "./data/info_" + user_id + ".json"
        storeInfo(personal_info, path)

        msg_to_chatGPT = "你是一名健身教練linebot，請根據以下的客戶資料，提供一個適合的健身計畫，請注意，你不需要看計畫開始時間的欄位:\n"
        for key in personal_info:
            msg_to_chatGPT += key + ":" + personal_info[key] + " "
        msg_to_chatGPT += "\n並根據以下的格式，制定出每個週次的每日計畫，每個週次都需要包含第1天至第7天，若是規劃時間超過使用者想要運動的時間，可以將當日設定成休息日，請不要將休息日全部規劃在前幾天或是後幾天，請交錯排序休息日。請將運動替換成符合使用者提供資料的運動項目，每天不需要將所有使用者指定的運動安排上去，並用 - 當作每日健身計畫中，每個項目開頭。\n"
        msg_to_chatGPT += "例如:\n"
        msg_to_chatGPT += "週次1:\n"
        msg_to_chatGPT += "第1天:\n"
        msg_to_chatGPT += "- 運動1 時間\n"
        msg_to_chatGPT += "- 運動2 時間\n"
        msg_to_chatGPT += "- 運動3 時間\n"
        msg_to_chatGPT += "------------------\n"

        msg_to_chatGPT += "除此之外，如果之後使用者想要更改健身計畫，請要求使用者輸入'@reenter'。\n"
        msg_to_chatGPT += "請在回覆訊息中，提示使用者輸入'@save'以儲存計畫，以及提示使用者輸入'@reenter'以更改計畫，\n"
        msg_to_chatGPT += "若使用者的時間要求不符合，請敘述不合理的原因，並不要產生健身計畫，並要求使用者輸入'@reenter'以更改計畫。不合理的要求包含但不限於: 在一週內減少10公斤\n"

        # print(msg_to_chatGPT)
        history_path = "./data/history_" + user_id + ".json"

        response_message = chat(msg_to_chatGPT, getHistory(history_path), history_path)
        linebot_chat(
            event,
            message=response_message,
        )

        init_finish = True
    elif event.message.text == "@reenter":
        info_index = 1
        personal_info.clear()
        linebot_chat(event, "請問你的年齡是？")
    else:
        personal_info[info_keys[info_index - 1]] = event.message.text
        # pretty save the personal info into the msg
        msg = ""
        for key in personal_info:
            msg += "\n" + key + ":" + personal_info[key]
        linebot_chat(
            event,
            "請問以下您的個人資料是否正確？\n" + msg + "\n" + "若正確請輸入'@confirm'，否則請輸入'@reenter'",
        )

def handle_reset_event(event):
    global init_finish
    global info_index
    global personal_info
    global modify_plan
    init_finish = False
    info_index = 0
    modify_plan = False
    personal_info.clear()
    files = os.listdir("./data")
    for file in files:
        if file.endswith(".json"):
            os.remove("./data/" + file)
    linebot_chat(event, "已經重置了，請輸入'@start'來重新開始")
    
def handle_reenter_event(event):
    global modify_plan
    linebot_chat(event, "請問你想要修改哪個健身計劃呢?")
    modify_plan = True

def handle_modify_plan_event(event):
    global modify_plan
    history_path = "./data/history_" + event.source.user_id + ".json"
    history = getHistory(history_path)
    msg_to_chatGPT = event.message.text
    reply_message = chat(msg_to_chatGPT, history, history_path)
    linebot_chat(
        event,
        reply_message + "\n如果同意上述的健身計畫，請輸入'@save'，否則請輸入'@reenter'",
    )
    modify_plan = False
    
def handle_plan_event(event):
    plan_path = "./data/plan_" + event.source.user_id + ".json"
    reply_message = "以下是您的健身計畫:\n"
    with open(plan_path, "r") as f:
        reply_message = f.read()
    linebot_chat(event, reply_message)
    
def handle_save_event(event):
    global modify_plan
    history_path = "./data/history_" + event.source.user_id + ".json"
    plan_path = "./data/plan_" + event.source.user_id + ".json"
    user_path = "./data/userid.json"
    history = getHistory(history_path)
    msg_to_chatGPT = (
        "請根據之前的對話紀錄，將使用者的健身計畫整理成json的格式，不需要將客戶的個人資料記錄下來，只需要健身計畫即可。請勿輸出除了json格式以外的任何對話\n"
        "Example:\n"
        "{\n"
        '    "週次1": {\n'
        '        "第1天": [\n'
        '            "運動1",\n'
        '            "運動2",\n'
        '            "運動3"\n'
        "        ],\n"
        '        "第2天": [\n'
        '            "運動1",\n'
        '            "運動2",\n'
        '            "運動3"\n'
        "        ],\n"
        '        "第3天": [\n'
        '            "運動1",\n'
        '            "運動2",\n'
        '            "運動3"\n'
        "        ],\n"
        "        ...\n"
        "    },\n"
        '    "週次2": {\n'
        '        "第1天": [\n'
        '            "運動1",\n'
        '            "運動2",\n'
        '            "運動3"\n'
        "        ],\n"
        "        ...\n"
        "    },\n"
        "    ...\n"
        "}\n"
    )
    reply_message = chat(msg_to_chatGPT, history, history_path)
    with open(plan_path, "w") as f:
        f.write(reply_message)
    storeInfo(event.source.user_id, user_path)
    modify_plan = False
    linebot_chat(event, "健身計畫已儲存")

def handle_finish_event(event):
    global finish_plan 
    finish_plan = True
    reply_message = "請問您完成了哪些項目呢?(請輸入週次幾, 第幾天, 哪些項目)\n"
    linebot_chat(event, reply_message)
    
    # read the plan and send it to chatGPT to get the response
def handle_finish_plan_event(event):
    global finish_plan
    finish_plan = False
    with open("./data/plan_" + event.source.user_id + ".json", "r") as f:
        plan = json.loads(f.read())
    msg_to_chatGPT = event.message.text
    msg_to_chatGPT += "以下是原本的健身計畫內容:\n"
    msg_to_chatGPT += json.dumps(plan, ensure_ascii=False, indent=4)
    msg_to_chatGPT += "\n請根據用戶的訊息，修改健身計畫，並輸出修改過後json格式的健身計畫，請勿輸出除了json格式以外的任何對話"
    history_path = "./data/history_" + event.source.user_id + ".json"
    history = getHistory(history_path)
    reply_message = chat(msg_to_chatGPT, history, history_path)
    # write the plan to the file
    with open("./data/plan_" + event.source.user_id + ".json", "w") as f:
        f.write(reply_message)
    # use sticker to reply and send some message to motivate the user
    line_bot_api.reply_message(
        event.reply_token,
        [
            StickerSendMessage(package_id=446, sticker_id=1989),
            TextSendMessage(text="加油! 你可以的!"),
        ],
    )
    
    
def handle_other_event(event):
    history_path = "./data/history_" + event.source.user_id + ".json"
    history = getHistory(history_path)
    response_message = chat(event.message.text, history, history_path)
    linebot_chat(event, response_message)
    
@csrf_exempt
def callback(request):
    if request.method == "POST":
        signature = request.META["HTTP_X_LINE_SIGNATURE"]
        body = request.body.decode("utf-8")

        try:
            events = parser.parse(body, signature)  # 傳入的事件
        except InvalidSignatureError:
            return HttpResponseForbidden()
        except LineBotApiError:
            return HttpResponseBadRequest()

        for event in events:
            if isinstance(event, MessageEvent):
                handle_message_event(event)
        return HttpResponse()
    else:
        return HttpResponseBadRequest()

def handle_message_event(event):
    global init_finish
    global modify_plan
    global finish_plan
    
    # init_finish = True
    if event.message.text == "@reset":
        handle_reset_event(event)
    elif not init_finish:
        init(event)
    elif modify_plan:
        handle_modify_plan_event(event)
    elif finish_plan:
        handle_finish_plan_event(event)
    elif event.message.text == "@save":
        handle_save_event(event)
    elif event.message.text == "@reenter":
        handle_reenter_event(event)
    elif event.message.text == "@plan":
        handle_plan_event(event)
    elif event.message.text == "@finish":
        handle_finish_event(event)
    else:
        handle_other_event(event)