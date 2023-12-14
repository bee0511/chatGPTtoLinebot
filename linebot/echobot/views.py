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
from mylinebot.secret import OPENAI_API_KEY

line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY

chat_button = False

history = []


def chat(message):
    history.append({"role": "user", "content": message + " 請用繁體中文回答"})
    response = openai.chat.completions.create(model="gpt-3.5-turbo", messages=history)
    response_message = response.choices[0].message
    history.append({"role": response_message.role, "content": response_message.content})

    return response_message.content


@csrf_exempt
def callback(request):
    global chat_button
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
                if "hello" in event.message.text:
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text="HIIIII!!!")
                    )
                elif event.message.text == "@sticker":  # Send sticker
                    try:
                        message = StickerSendMessage(
                            package_id="6136", sticker_id="10551377"
                        )
                        line_bot_api.reply_message(event.reply_token, message)
                    except:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text="Error, please try again."),
                        )
                elif event.message.text == "@image":  # Send image
                    try:
                        message = ImageSendMessage(
                            original_content_url="https://images.pexels.com/photos/1108099/pexels-photo-1108099.jpeg",
                            preview_image_url="https://images.pexels.com/photos/1108099/pexels-photo-1108099.jpeg",
                        )
                        line_bot_api.reply_message(event.reply_token, message)
                    except:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text="Error, please try again."),
                        )
                elif event.message.text == "@location":  # Send location
                    try:
                        message = LocationSendMessage(
                            title="交大",
                            address="NYCU",
                            latitude=24.78646579287709,
                            longitude=120.99814786241119,
                        )
                        line_bot_api.reply_message(event.reply_token, message)
                    except:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text="Error, please try again."),
                        )
                elif event.message.text == "@chatGPT":  # Chat with GPT-3.5
                    try:
                        chat_button = not chat_button
                        if chat_button:
                            history.clear()
                            line_bot_api.reply_message(
                                event.reply_token,
                                TextSendMessage(text="ChatGPT is on."),
                            )
                        else:
                            line_bot_api.reply_message(
                                event.reply_token,
                                TextSendMessage(text="ChatGPT is off."),
                            )
                    except:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text="Error, please try again."),
                        )
                elif chat_button:
                    try:
                        reply = chat(event.message.text.strip())
                        line_bot_api.reply_message(
                            reply_token=event.reply_token,
                            messages=TextSendMessage(text=reply),
                        )
                    except:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text="Error, please try again."),
                        )
                else:
                    line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=event.message.text)
                    )
        return HttpResponse()
    else:
        return HttpResponseBadRequest()
