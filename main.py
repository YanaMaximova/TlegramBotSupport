
import asyncio
import logging
from sulguk import AiogramSulgukMiddleware
from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.chat_action import ChatActionMiddleware
import config
from datetime import datetime
from pytz import timezone
from handlers import router
import text
from firebase.firebase import (
    get_config, add_document, \
    upload_file, read_collection, \
    read_document, download_file, \
    update_document, delete_document, \
    read_document_with_filter, delete_file, \
    read_collection_with_composite_filter
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from collection_editer import outstanding, upcoming, overdue
from kb import create_pagination_keyboard, create_title_menu
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.state import State, StatesGroup, default_state
class FSMStates(StatesGroup):
    '''states for bot'''
    wait_calendar_name = State()
    # waiting to receive information about available events for confirmation
    selected_calendar = State()
    waiting_for_start_comment = State()
    # waiting end comment
    waiting_for_end_comment = State()
    # waiting comments are deleted
    waiting_for_end_cancel_comment = State()
    waiting_for_end_loading_message = State()
    waiting_for_end_start = State()
    waiting_for_end_confirm = State()
    wait_menu_click = State()
    waiting_more_info = State()
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

async def clear_chat_cron(bot: Bot, dp: Dispatcher):
    farmers = read_collection("farmers")
    firebase_config = get_config()
    tz = timezone(firebase_config['timezone'])
    time = datetime.now(tz=tz)
    for farmer in farmers:
        greating = None        
        try:
            history = read_collection_with_composite_filter(
                collection = "history_message_id",
                filters = [
                {
                    "atribut": "tg_id",
                    "op": "==",
                    "value": farmer["data"]["tg_id"],
                },
                {
                    "atribut": "bot",
                    "op": "==",
                    "value": "farmer_task",
                }
                ])
        except:
            history = []
       
        if len(history) == 0:
            menu = [f'Farm\'s Calendar', f'Farmer\'s Log Book', f'My Payment Plan', f'Support']
            buttons = ["Farm's Calendar", "Farmer's Log Book", "Payment", "Support"]
            try:
                
                try: 
                    greating = await bot.send_message(
                    text=f'Hi, here are some things I can help with:',
                    reply_markup=create_title_menu([name for name in menu], [button for button in buttons]),
                    parse_mode=ParseMode.MARKDOWN,
                    chat_id=farmer["data"]["tg_id"]
                    )
                except TelegramForbiddenError:
                    print(f'''User blocked  {farmer["data"]["tg_id"]}''')
               
                state_with = FSMContext(
                    storage=dp.storage, # dp - экземпляр диспатчера 
                    key=StorageKey(
                    chat_id=farmer["data"]["tg_id"], # если юзер в ЛС, то chat_id=user_id
                    user_id=farmer["data"]["tg_id"],  
                    bot_id=bot.id
                    )
                )

                await state_with.set_state(FSMStates.wait_menu_click)
                for i in range(greating.message_id - 1, 0, -1):
                    try:
                        await bot.delete_message(farmer["data"]["tg_id"], i)
                    except TelegramBadRequest as ex:
                        if ex.message == "Bad Request: message to delete not found":
                            print("All messages deleted")
                add_document(
                    {
                        "tg_id": farmer["data"]["tg_id"],
                        "first_message_id": greating.message_id,
                        "bot": "farmer_task"
                    
                    },
                    collection = "history_message_id"
                )
            except:
                print(f'''Problem clear chat user_id: {farmer["data"]["tg_id"]}''')
                
        elif len(history) == 1:
            menu = [f'Farm\'s Calendar', f'Farmer\'s Log Book', f'My Payment Plan', f'Support']
            buttons = ["Farm's Calendar", "Farmer's Log Book", "Payment", "Support"]
            try:
                try:
                    greating = await bot.send_message(
                    text=f'Hi, here are some things I can help with:',
                    reply_markup=create_title_menu([name for name in menu], [button for button in buttons]),
                    parse_mode=ParseMode.MARKDOWN,
                    chat_id=farmer["data"]["tg_id"]
                    )
                except TelegramForbiddenError:
                    print(f'''User blocked  {farmer["data"]["tg_id"]}''')
                state_with = FSMContext(
                    storage=dp.storage, # dp - экземпляр диспатчера 
                    key=StorageKey(
                    chat_id=farmer["data"]["tg_id"], # если юзер в ЛС, то chat_id=user_id
                    user_id=farmer["data"]["tg_id"],  
                    bot_id=bot.id
                    )
                )

                await state_with.set_state(FSMStates.wait_menu_click) 
                for i in range(history[0]["data"]["first_message_id"], greating.message_id):
                    try:
                        await bot.delete_message(farmer["data"]["tg_id"], i)
                    except TelegramBadRequest as ex:
                        if ex.message == "Bad Request: message to delete not found":
                            print("All messages deleted")
                update_document(
                    history[0]["document_id"],
                    {
                        "tg_id": farmer["data"]["tg_id"],
                        "first_message_id": greating.message_id,
                        "bot": "farmer_task"
                    },
                    collection = "history_message_id"
                )
            except:
                print(f'''Problem clear chat user_id: {farmer["data"]["tg_id"]}''')
        else:
            first_message_id = history[0]["data"]["first_message_id"]
            doc_id = history[0]["document_id"]
            for i in range(1, len(history)):
                if history[i]["data"]["first_message_id"] > first_message_id:
                    delete_document(doc_id, collection = "history_message_id")
                    doc_id = history[i]["document_id"]
                    first_message_id = history[i]["data"]["first_message_id"]
                else:
                    delete_document(history[i]["document_id"], collection = "history_message_id")
            menu = [f'Farm\'s Calendar', f'Farmer\'s Log Book', f'My Payment Plan', f'Support']
            buttons = ["Farm's Calendar", "Farmer's Log Book", "Payment", "Support"]
            try:
                try:
                    greating =  await bot.send_message(
                    text=f'Hi, here are some things I can help with:',
                    reply_markup=create_title_menu([name for name in menu], [button for button in buttons]),
                    parse_mode=ParseMode.MARKDOWN,
                    chat_id=farmer["data"]["tg_id"]
                    )
                except TelegramForbiddenError:
                    print(f'''User blocked  {farmer["data"]["tg_id"]}''')
                state_with = FSMContext(
                    storage=dp.storage, # dp - экземпляр диспатчера 
                    key=StorageKey(
                    chat_id=farmer["data"]["tg_id"], # если юзер в ЛС, то chat_id=user_id
                    user_id=farmer["data"]["tg_id"],  
                    bot_id=bot.id
                    )
                )

                await state_with.set_state(FSMStates.wait_menu_click) 
                for i in range(first_message_id, greating.message_id):
                    try:
                        await bot.delete_message(farmer["data"]["tg_id"], i)
                    except TelegramBadRequest as ex:
                        if ex.message == "Bad Request: message to delete not found":
                            print("All messages deleted")
                update_document(
                    doc_id,
                    {
                        "tg_id": farmer["data"]["tg_id"],
                        "first_message_id": greating.message_id,
                        "bot": "farmer_task"
                    },
                    collection = "history_message_id"
                )
            except:
                print(f'''Problem clear chat user_id: {farmer["data"]["tg_id"]}''')
        
async def overdue_notify_farmer(bot: Bot):
    farmers = read_collection("farmers")
    firebase_config = get_config()
    tz = timezone(firebase_config['timezone'])
    time = datetime.now(tz=tz)
    for farmer in farmers:
        overdue_events = overdue(farmer["data"]["tg_id"])
        for calendar_event in overdue_events:
            time_before_begin = int((time - calendar_event["data"]["timestamp_end"]).total_seconds() / (60 * 60 * 24))
            title = calendar_event["data"]["title"]
            if  time_before_begin:
                try:
                    await bot.send_message(text=text.notify_overdue.format(title, time_before_begin), reply_markup=create_title_menu(["Got it!"], ["Got it!"]), chat_id=farmer["data"]["tg_id"], parse_mode=ParseMode.MARKDOWN)
                except:
                    print("Problem with chat. Telegram id: {}".format(farmer["data"]["tg_id"]))

async def outstanding_notify_farmer(bot: Bot):
    farmers = read_collection("farmers")
    firebase_config = get_config()
    tz = timezone(firebase_config['timezone'])
    time = datetime.now(tz=tz)
    for farmer in farmers:
        outstanding_events = outstanding(farmer["data"]["tg_id"])
        for calendar_event in outstanding_events:
            date_end = calendar_event["data"]["timestamp_end"].strftime("%d %B %Y")
            title = calendar_event["data"]["title"]
            try:
                await bot.send_message(text=text.notify_outstanding.format(title, date_end), reply_markup=create_title_menu(["Got it!"], ["Got it!"]), chat_id=farmer["data"]["tg_id"], parse_mode=ParseMode.MARKDOWN)
            except:
                print("Problem with chat. Telegram id: {}".format(farmer["data"]["tg_id"]))

   

async def upcoming_notify_farmer(bot: Bot):
    farmers = read_collection("farmers")
    firebase_config = get_config()
    tz = timezone(firebase_config['timezone'])
    time = datetime.now(tz=tz)
    
    for farmer in farmers:
        calendar_events = read_collection_with_composite_filter(
        "calendar_events",
        [
            {
                "atribut": "farmer_tg_id",
                "op": "==",
                "value": farmer["data"]["tg_id"],
            },
            {
                "atribut": "status",
                "op": "==",
                "value": "creation",
            },

        ],
        {
            "atribut": "timestamp_begin",
            "desc": False
        }
        )
        notify_id = []
        for calendar_event in calendar_events:
            minuts_before = calendar_event["data"]["notify_for_days"] * 24 * 60
            time_before_begin = (time - calendar_event["data"]["timestamp_begin"]).total_seconds() / 60
            if calendar_event["data"]["status"] == "creation" and  time_before_begin > -minuts_before and time_before_begin < 0:
                notify_id.append(calendar_event["document_id"])
        for event_id in notify_id:
            update_document(
                event_id,
                {
                    "status": "notified_farmer"
                },
                collection = "calendar_events"
            )
            event = read_document(event_id, "calendar_events")
            title = event["title"]
            date_begin = event["timestamp_begin"].strftime("%d %B %Y")
            try:
                await bot.send_message(text=text.notify_upcoming.format(title, date_begin), reply_markup=create_title_menu(["Got it!"], ["Got it!"]), chat_id=farmer["data"]["tg_id"], parse_mode=ParseMode.MARKDOWN)
            except:
                print("Problem with chat. Telegram id: {}".format(farmer["data"]["tg_id"]))

async def briefing_for_farmer(bot: Bot):
    farmers = read_collection("farmers")
    firebase_config = get_config()
    tz = timezone(firebase_config['timezone'])
    time = datetime.now(tz=tz)
    
    for farmer in farmers:
        print(farmer)
        calendar_events = read_document_with_filter(
            atribut = "farmer_tg_id",
            op = "==",
            value = farmer["data"]["tg_id"],
            collection = "calendar_events"
        )
        calendar_name = ["Upcoming", "Outstanding", "Overdue"]
        upcoming_events = upcoming(farmer["data"]["tg_id"])
        outstanding_events = outstanding(farmer["data"]["tg_id"])
        overdue_events = overdue(farmer["data"]["tg_id"])
        msg = ""
        upcoming_text = []
        for event in upcoming_events:
            title = event["data"]["title"]
            date_begin = event["data"]["timestamp_begin"].strftime("%d %B %Y")
            upcoming_text.append(f'\t{title} *Available From:* {date_begin}\n')
        if len(upcoming_text) > 0:
            msg = ''.join((msg, f'✅ ({len(upcoming_events)}) Upcoming\n\n'))
            msg = ''.join((msg, '\n'.join(upcoming_text), "\n"))
        if len(outstanding_events) > 0:
            msg = ''.join((msg, f'⚠️ ({len(outstanding_events)}) Outstanding\n\n'))
        if len(overdue_events) > 0:
            msg = ''.join((msg, f'❗️ ({len(overdue_events)}) Overdue\n\n'))
        try:
            if len(msg) > 0:
                await bot.send_message(text=text.notify_briefing.format(farmer["data"]["personal_info"]["name"], time.strftime("%d %B %Y"), msg), reply_markup=create_title_menu(["Got it!"], ["Got it!"]), chat_id=farmer["data"]["tg_id"], parse_mode=ParseMode.MARKDOWN)
            else:
                await bot.send_message(text=text.notify_empty.format(farmer["data"]["personal_info"]["name"], time.strftime("%d %B %Y")), reply_markup=create_title_menu(["Got it!"], ["Got it!"]), chat_id=farmer["data"]["tg_id"], parse_mode=ParseMode.MARKDOWN)
                
        except:
            print("Problem with chat. Telegram id: {}".format(farmer["data"]["tg_id"]))


    
async def main():
    firebase_config = get_config()
    tz=timezone(firebase_config['timezone'])
    bot = Bot(token=config.BOT_TOKEN, parse_mode=ParseMode.HTML)
    bot.session.middleware(AiogramSulgukMiddleware())
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(ChatActionMiddleware())
    dp.include_router(router)
    executors = {
        'default': ThreadPoolExecutor(20),
        'processpool': ProcessPoolExecutor(5)
    }

    jobDefaults = {
        'coalesce': True,
        'max_instances': 100,
        'misfire_grace_time': 10*60
    }

    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(
        func=clear_chat_cron,
        id="clear chat",
        trigger='interval',
        start_date=datetime(2024, 2, 27, 22,50,0),
        #minutes=60,
        #seconds=20,
        hours=24,
        misfire_grace_time=60*5,
        kwargs={"bot": bot, "dp": dp}
    )
    scheduler.add_job(
        upcoming_notify_farmer,
        trigger='interval',
        start_date=datetime(2024, 2, 27, 16, 0, 0),
        #minutes=60,
        #seconds=20,
        hours=6,
        timezone=tz,
        misfire_grace_time=60*5,
        kwargs={"bot": bot}
    )
    scheduler.add_job(
        outstanding_notify_farmer,
        trigger='interval',
        start_date=datetime(2024, 2, 27, 16, 30, 0),
        #minutes=60,
        #seconds=20,
        hours=6,
        timezone=tz,
        misfire_grace_time=60*5,
        kwargs={"bot": bot}
    )
    scheduler.add_job(
        overdue_notify_farmer,
        trigger='interval',
        start_date=datetime(2024, 2, 27, 17, 0, 0),
        #minutes=60,
        #seconds=20,
        hours=6,
        timezone=tz,
        misfire_grace_time=60*5,
        kwargs={"bot": bot}
    )
    scheduler.add_job(
        briefing_for_farmer,
        trigger='interval',
        start_date=datetime(2024, 2, 27, 17, 30, 0),
        #minutes=5,
        #seconds=20,
        hours=6,
        timezone=tz,
        misfire_grace_time=60*5,
        kwargs={"bot": bot}
    )
    scheduler.start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())



