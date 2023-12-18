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
import json
from mylinebot.secret import OPENAI_API_KEY


line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY

init_finish = False
personal_info = {}


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


def storeInfo(message):
    """Store the personal info to the info.json"""
    with open("./data/info.json", "w") as f:
        f.write(message)


def chat(message, history):
    history.append({"role": "user", "content": message + " 請用繁體中文回答"})
    response = openai.chat.completions.create(model="gpt-3.5-turbo", messages=history)
    response_message = response.choices[0].message
    history.append({"role": response_message.role, "content": response_message.content})

    return response_message.content


def linebot_chat(event, message):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=message),
    )


info_index = 0
info_keys = ["年齡", "性別", "身高(cm)", "體重(kg)", "運動習慣(每週幾次)", "目標", "計畫時間長度(週)"]


def init(event):
    global info_index
    global init_finish
    if info_index < len(info_keys):
        if info_index > 0:
            personal_info[info_keys[info_index - 1]] = event.message.text
        message = "請問你的" + info_keys[info_index] + "是? "
        if info_index == 5:
            message += "(減重/增重到幾公斤)"

        linebot_chat(event, message=message)
        info_index += 1
    elif event.message.text == "@confirm":
        storeInfo(json.dumps(personal_info, ensure_ascii=False, indent=4))

        msg_to_chatGPT = "你是一名健身教練，請根據以下的客戶資料，提供一個適合的健身計畫:\n"
        for key in personal_info:
            msg_to_chatGPT += key + ":" + personal_info[key] + " "
        msg_to_chatGPT += "\n並根據以下的格式，制定出每個週次的每日計畫，並用 - 當作每日健身計畫中，當作每日健身計畫的每個項次開頭:\n"
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
        
        print(msg_to_chatGPT)

        history = getHistory()
        history.append({"role": "user", "content": msg_to_chatGPT})
        # response = openai.chat.completions.create(
        #     model="gpt-3.5-turbo", messages=history
        # )
        # response_message = response.choices[0].message
        # history.append(
        #     {"role": response_message.role, "content": response_message.content}
        # )
        storeHistory(history)
        linebot_chat(event, message=msg_to_chatGPT)

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
                if not init_finish:
                    init(event)
                    return HttpResponse()
                history = getHistory()
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=event.message.text)
                )
        return HttpResponse()
    else:
        return HttpResponseBadRequest()
