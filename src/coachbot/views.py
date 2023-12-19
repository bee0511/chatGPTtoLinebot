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
    ImageSendMessage,
    LocationSendMessage,
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


def getHistory():
    """Read the chat history from the history.json"""
    history = []
    # test file exist, if not exict, create one
    try:
        with open("./data/history.json", "r") as f:
            history = json.loads(f.read())
    except:
        with open("./data/history.json", "w") as f:
            f.write(json.dumps(history, ensure_ascii=False, indent=4))
    return history


def storeHistory(history):
    """Store the chat history to the history.json"""
    with open("./data/history.json", "w") as f:
        f.write(json.dumps(history, ensure_ascii=False, indent=4))


def storeInfo(message, path):
    """Store the info like personal info and plan to the info.json and plan.json"""
    with open(path, "w") as f:
        f.write(message)


def chat(message, history):
    history.append({"role": "user", "content": message + " 請用繁體中文回答"})
    response = openai.chat.completions.create(model="gpt-3.5-turbo", messages=history)
    response_message = response.choices[0].message
    history.append({"role": response_message.role, "content": response_message.content})
    storeHistory(history)
    return response_message.content


def linebot_chat(event, message):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=message),
    )


info_index = 0
info_keys = ["年齡", "性別", "身高(cm)", "體重(kg)", "每週想運動的日期", "目標", "計畫時間長度(週)"]


def init(event):
    global info_index
    global init_finish
    if info_index < len(info_keys):
        if info_index > 0:
            personal_info[info_keys[info_index - 1]] = event.message.text
        message = "請問你的" + info_keys[info_index] + "是? "
        if info_index == 4:
            message += "(請用逗號分隔，例如: 週一,週三,週五)"
        elif info_index == 5:
            message += "(減重/增重到幾公斤)"

        linebot_chat(event, message=message)
        info_index += 1
    elif event.message.text == "@confirm":
        storeInfo(
            json.dumps(personal_info, ensure_ascii=False, indent=4), "./data/info.json"
        )

        msg_to_chatGPT = "你是一名健身教練linebot，請根據以下的客戶資料，提供一個適合的健身計畫:\n"
        for key in personal_info:
            msg_to_chatGPT += key + ":" + personal_info[key] + " "
        msg_to_chatGPT += "\n並根據以下的格式，制定出每個週次的每日計畫，並用 - 當作每日健身計畫中，當作每日健身計畫的每個項次開頭，請根據使用者可以運動的日子建議計畫。\n"
        msg_to_chatGPT += "例如:\n"
        msg_to_chatGPT += "週次1:\n"
        msg_to_chatGPT += "週一:\n"
        msg_to_chatGPT += "- 慢跑5公里\n"
        msg_to_chatGPT += "- 伏地挺身20下\n"
        msg_to_chatGPT += "- 仰臥起坐20下\n"
        msg_to_chatGPT += "------------------\n"
        msg_to_chatGPT += "週二:\n"
        msg_to_chatGPT += "- 游泳30分鐘\n"
        msg_to_chatGPT += "- 伏地挺身20下\n"
        msg_to_chatGPT += "- 仰臥起坐20下\n"
        msg_to_chatGPT += "------------------\n"

        msg_to_chatGPT += "除此之外，如果之後使用者想要更改健身計畫，請要求使用者輸入'@reenter'。"

        # print(msg_to_chatGPT)

        response_message = chat(msg_to_chatGPT, getHistory())
        linebot_chat(
            event,
            message=response_message + "\n若有需要修改健身計畫，請輸入'@reenter'\n若不需要修改，請輸入'@save'",
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


@csrf_exempt
def callback(request):
    global init_finish
    global info_index
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
                if event.message.text == "@reset":
                    init_finish = False
                    info_index = 0
                    personal_info.clear()
                    if os.path.exists("./data/info.json"):
                        os.remove("./data/info.json")
                    if os.path.exists("./data/plan.json"):
                        os.remove("./data/plan.json")
                    if os.path.exists("./data/history.json"):
                        os.remove("./data/history.json")
                    linebot_chat(event, "已經重置了，請輸入'@start'來重新開始")
                    return HttpResponse()
                elif not init_finish:
                    init(event)
                    return HttpResponse()
                elif event.message.text == "@save":
                    history = getHistory()
                    msg_to_chatGPT = (
                        "請根據之前的對話紀錄，將使用者的健身計畫整理成json的格式，只需要輸出json的格式，不需要輸出任何對話"
                    )
                    reply_message = chat(msg_to_chatGPT, history)
                    storeInfo(reply_message, "./data/plan.json")
                    linebot_chat(event, "健身計畫已儲存")
                    return HttpResponse()
                elif event.message.text == "@reenter":
                    linebot_chat(event, "請問你想要修改哪個健身計劃呢?")
                    modify_plan = True
                    return HttpResponse()
                elif modify_plan:
                    history = getHistory()
                    msg_to_chatGPT = event.message.text
                    reply_message = chat(msg_to_chatGPT, history)
                    linebot_chat(
                        event,
                        reply_message + "\n如果同意上述的健身計畫，請輸入'@save'，否則請輸入'@reenter'",
                    )
                    modify_plan = False
                    return HttpResponse()
                else:
                    history = getHistory()
                    response_message = chat(event.message.text, history)
                    linebot_chat(event, response_message)
        return HttpResponse()
    else:
        return HttpResponseBadRequest()
