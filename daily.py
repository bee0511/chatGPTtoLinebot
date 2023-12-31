import json
from linebot import LineBotApi
from linebot.models import TextSendMessage, StickerSendMessage
from apscheduler.schedulers.blocking import BlockingScheduler
from secret import HIDDEN_LINE_CHANNEL_ACCESS_TOKEN

# 建立 LineBotApi 實例
line_bot_api = LineBotApi(HIDDEN_LINE_CHANNEL_ACCESS_TOKEN)

# 建立一個字典來儲存每個使用者的進度
progress = {}

def push_daily_plan():
    # 讀取所有的使用者 ID
    with open("./data/userid.json", "r", encoding='utf-8') as f:
        user_ids = json.load(f)

    # 遍歷每一個使用者
    for user_id in user_ids:
        # 如果該使用者還沒有進度，則初始化為 0
        if user_id not in progress:
            progress[user_id] = 0

        # 讀取該使用者的健身計畫
        with open(f"./data/plan_{user_id}.json", "r", encoding='utf-8') as f:
            plan = json.load(f)

        # 計算應該推送哪一天的健身計畫
        days_passed = progress[user_id]
        week = days_passed // 7 + 1
        day = days_passed % 7 + 1

        # 獲取當日的健身計畫
        daily_plan = plan.get(f"週次{week}", {}).get(f"第{day}天", [])

        message = "今日健身計畫：\n"
        
        # 將健身計畫轉換為文字訊息
        message += "\n".join(daily_plan)

        # 使用 push_message 方法推送訊息
        line_bot_api.push_message(user_id, [TextSendMessage(text=message), StickerSendMessage(package_id='446', sticker_id='1989')])
        # 更新該使用者的進度
        progress[user_id] += 1
# 建立排程器
sched = BlockingScheduler()

# 設定排程任務，每日早上6點執行一次 push_daily_plan 函數
# sched.add_job(push_daily_plan, 'cron', hour=6)

# 設定排程任務，每5秒鐘執行一次 push_daily_plan 函數
sched.add_job(push_daily_plan, 'interval', seconds=5)


# 開始執行排程任務
sched.start()