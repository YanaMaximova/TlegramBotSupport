from aiogram import types, F, Router, flags, Bot, Dispatcher
from aiogram.types import (
    ReplyKeyboardRemove, ReplyKeyboardMarkup, \
    KeyboardButton, InlineKeyboardMarkup, \
    InlineKeyboardButton, FSInputFile, \
    URLInputFile, BufferedInputFile, \
    Message, ReplyKeyboardRemove
)
from farmer2agronom import farmer2agronom
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram_media_group import media_group_handler
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
import os
import logging
from firebase.firebase import (
    get_config, add_document, \
    upload_file, read_collection, \
    read_document, download_file, \
    update_document, delete_document, \
    read_document_with_filter, delete_file, \
    read_collection_with_composite_filter, update_document_array
)
from kb import create_menu
from bd_and_DataFrame import add_information, merge_and_sortes_message_about_problems
from sulguk import SULGUK_PARSE_MODE
from collection_editer import download_information
from aiogram.enums.parse_mode import ParseMode
import asyncio
from aiogram.filters import Command, StateFilter, CommandStart
from aiogram import F
from datetime import datetime
from pytz import timezone
import requests
from kb import create_pagination_keyboard, create_title_menu
import kb, text
from pagination_info import DataFramePaginator
import pandas as pd
from text_message import event_brief_information, event_full_information

router = Router()

from aiogram.types.error_event import ErrorEvent

@router.error()
async def error_handler(event: ErrorEvent):
    logging.critical("Critical error caused by %s", event.exception, exc_info=True)

def check_farmer(tg_id: int) -> bool:
    '''
    Check farmer with tg_id from telegram message to exist in collection "farmers"
    
    Args:
        tg_id: int
            tg_id from telegram message
    '''
    farmers = read_collection("farmers")
    tg_id_farmers = [farmer["data"]["tg_id"] for farmer in farmers]
    #return tg_id in tg_id_farmers
    return True

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
    
@router.message(StateFilter(FSMStates.waiting_for_end_start))
@router.message(StateFilter(FSMStates.waiting_for_end_loading_message))
async def send_available_data_to_confirmation(message: types.Message, state: FSMContext):
    '''Do not respond until all messages from the farmer are sent'''
    try:
        await message.delete()
    except:
        print(f'Error clean {message.from_user.id} message_id: {message.message_id}')
        
@router.message(StateFilter(FSMStates.waiting_for_end_loading_message))
async def wait_loading(message: types.Message, state: FSMContext):
    await message.answer("Wait for messages to finish sending")
    try:
        await message.delete()
    except:
        print(f'Error clean {message.from_user.id} message_id: {message.message_id}')

@router.message(CommandStart())        
@router.message(CommandStart(), StateFilter(default_state))
@router.message(StateFilter(default_state), F.text == "start")
@router.message(StateFilter(default_state), Command("start"))
async def process_start_command(message: types.Message, state: FSMContext):
    logging.basicConfig(level=logging.DEBUG)
    if check_farmer(message.from_user.id):
        logging.basicConfig(level=logging.DEBUG)
        menu = [f'Crop Calendar', f'Agronomics Support']
        buttons = ["Crop Calendar", "Support"]
        await message.answer(
            text=f'Hi, here are some things I can help with:',
            reply_markup=create_title_menu([name for name in menu], [button for button in buttons]),
            parse_mode=ParseMode.MARKDOWN
        )
        await state.set_state(FSMStates.wait_menu_click)
        
@router.callback_query(F.data.startswith('Got it!'))
async def briefing(call: types.CallbackQuery):
    await call.message.delete()

class FSMStatus(StatesGroup):
    support = State()
    create_problem = State()
    start_chating = State()
    chating = State()
    
@router.callback_query(StateFilter(FSMStates.wait_menu_click), F.data.startswith('Support'))
async def support_menu(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        text.support(,
        reply_markup=create_menu(['Chating', 'New problem', 'back'], count=2),
        parse_mode=ParseMode.MARKDOWN

    )
    await state.set_state(FSMStatus.support)
    await state.update_data(
        {
            call.message.chat.id: {"message": []}
        }
    )
        
@router.callback_query(StateFilter(FSMStatus.create_problem), F.data.startswith('Return'))
async def start_handler_call(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer(
        text.support.format(call.from_user.full_name),
        reply_markup=create_menu(['Existing problems', 'New problem', 'back'], count=2)
    )
    await state.set_state(FSMStates.support)
    await state.update_data(
        {
            call.message.chat.id: {"message": []}
        }
    )
    
@router.callback_query(StateFilter(FSMStatus.start_chating), F.data.startswith('Return'))
@router.callback_query(StateFilter(FSMStatus.support), F.data.startswith('Return'))
async def start_handler_call(call: types.CallbackQuery, bot: Bot, state: FSMContext):
    await call.message.edit_text(
        text.support.format(call.from_user.full_name),
        reply_markup=create_menu(['Existing problems', 'New problem', 'back'], count=2)
    )
    await state.set_state(FSMStatus.support)
    data = await state.get_data()
    task = data.get(call.from_user.id)
    for  message_id in task["message"]:
        try:
            await bot.delete_message(call.message.chat.id, message_id)
        except:
            print(f'Error clean {call.message.chat.id} message_id: {message_id}')
    await state.update_data(
        {
            call.message.chat.id: {"message": []}
        }
    )
    
@router.callback_query(StateFilter(FSMStatus.support), F.data.startswith('New problem'))
async def create_problem_menu(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        text='Enter the name of your problem or click on the *Return* button to return to the main page',
        reply_markup=create_menu(['Return']),
        parse_mode=ParseMode.MARKDOWN
    )
    await state.set_state(FSMStatus.create_problem)

@router.message(StateFilter(FSMStatus.create_problem), F.text)
async def create_problem(message: types.Message, state: FSMContext, bot: Bot):
    df = download_information(int(message.from_user.id), 'problems_for_support')
    data = await state.get_data()
    task = data.get(message.from_user.id)
    msg_bot = task["message"]
    if len(df) and message.text in list(df["name"]):
        
        bot_message = await message.answer('''Enter another name, it's already taken''')
        msg_bot.append(bot_message.message_id)
        msg_bot.append(message.message_id)
        task["message"] = msg_bot
        await state.update_data(
            {
                message.from_user.id: task
            }
        )
        return
    add_document({
        'user_telegram_id': message.from_user.id,
        'number_of_messages': 0,
        'name': message.text,
        'status': "open"
        },
        collection='problems_for_support')
    await state.set_state(FSMStatus.support)
    bot_message = await message.answer(
        text='You have created a new question! *Return* to the main menu and click the *Chating* button to start a conversation',
        parse_mode=ParseMode.MARKDOWN
    )
    data = await state.get_data()
    task = data.get(message.from_user.id)
    msg_bot = task["message"]
    msg_bot.append(bot_message.message_id)
    msg_bot.append(message.message_id)
    task["message"] = msg_bot
    await state.update_data(
        {
            message.from_user.id: task
        }
    )
@router.callback_query(StateFilter(FSMStatus.support), F.data.startswith('Existing problems'))
async def chating_menu(call: types.CallbackQuery, state: FSMContext):
    df = download_information(int(call.from_user.id), 'problems_for_support')
    buttons = []
    for index, row in df.iterrows():
        button = row.to_dict()
        buttons.append((button['name'], button['number_of_messages']))
    await call.message.edit_text(
        text=f'You have the following problems:',
        reply_markup=create_menu([f'{button[0]} ({button[1]})' for button in buttons] + ['Return'],
                                 info=[button[0] for button in buttons] + ['Return']),
    )

    await state.set_state(FSMStatus.start_chating)

@router.callback_query(StateFilter(FSMStatus.chating), F.data.startswith('Return'))
async def start_handler_call(call: types.CallbackQuery, state: FSMContext):
    df = download_information(int(call.from_user.id), 'problems_for_support')
    buttons = []
    for index, row in df.iterrows():
        button = row.to_dict()
        buttons.append((button['name'], button['number_of_messages']))
    await call.message.edit_text(
        text=f'You have the following problems:',
        reply_markup=create_menu([f'{button[0]} ({button[1]})' for button in buttons] + ['Return'],
                                 info=[button[0] for button in buttons] + ['Return']),
    )
    await state.set_state(FSMStatus.start_chating)
    data = await state.get_data()
    task = data.get(call.from_user.id)
    for message_id in task["message"]:
        try:
            await bot.delete_message(call.message.chat.id, message_id)
        except:
            print(f'Error clean {call.message.chat.id} message_id: {message_id}')
    await state.update_data(
        {
            call.message.chat.id: {"message": []}
        }
    )

@router.callback_query(StateFilter(FSMStatus.start_chating))
async def chating(call: types.CallbackQuery, state: FSMContext):
    try:
        await state.set_state(FSMStatus.chating)
        problems = read_document_with_filter('user_telegram_id', '==', call.from_user.id, 'problems_for_support')
        message_chat = merge_and_sortes_message_about_problems(call.data, int(call.from_user.id))
        messages_id = [call.message.message_id]
        if  message_chat.empty:
            bot_message = await call.message.answer('Start chating!', reply_markup=create_menu(['Return'], count=1), parse_mode=ParseMode.MARKDOWN)
            messages_id.append(bot_message.message_id)
        else:
            for index, row in message_chat.iterrows():
                if row["type"] == "text":
                    msg = text.msg_from_chating(row)
                    if index == len(message_chat) - 1:
                        bot_message = await call.message.answer(text=msg, reply_markup=create_menu(['Return'], count=1), parse_mode=ParseMode.MARKDOWN)
                    else:
                        bot_message = await call.message.answer(text=msg, parse_mode=ParseMode.MARKDOWN)
                    messages_id.append(bot_message.message_id)
                elif row["type"] == "image":
                    path_on_cloud = row["path_on_cloud"]
                    path_local = '.'.join(
                    (
                        '_'.join(
                            (
                            "message_for_farmer",
                            str(call.message.chat.id),
                            str(call.message.date.strftime("%Y-%m-%d_%H-%M-%S"))
                            )
                        ),
                        'jpg'
                    )
                    )
                    download_file(path_on_cloud.item(), path_local)
                    image_from_pc = FSInputFile(path_local)
                    bot_message = await call.message.answer_photo(image_from_pc, caption=text.msg_from_chating(row))
                    if os.path.exists(path_local):
                        os.remove(path_local)
                    messages_id.append(bot_message.message_id)

        try:
            await call.message.delete()
        except:
            print('Error delete message')
    
        await state.update_data({call.from_user.id: {'problem': call.data, 'message': messages_id}})
    except:
        await state.set_state(FSMStatus.start_chating)

@router.message(StateFilter(FSMStatus.chating), F.media_group_id, F.content_type.in_({'photo'}))
@media_group_handler
async def album_handler(messages: List[types.Message], bot: Bot, state: FSMContext):
    '''Save group of images with caption'''
    if True:
        data = await state.get_data()
        task = data.get(messages[0].from_user.id)
        messages_id = messages[0].message_id
        firebase_config = get_config()
        tz=timezone(firebase_config['timezone'])
        delete_messages = []
        time = datetime.now(tz=tz)
        try:
            if messages[0].caption is not None:
                add_document(
                    {
                        "user_telegram_id": messages[0].from_user.id,
                        "message_id": messages_id,
                        "message_id_chat": messages_id,
                        "type": "text",
                        "time": messages[0].date,
                        "text": messages[0].caption,
                        "problem": task['problem']
                    }
                    ,
                    "telegram_message_from_farmer_for_support"
                )
                delete_messages.append(messages_id)
        except:
            raise print("Add document on cloud error")
        for index, msg in enumerate(messages):
            path_local = '.'.join(
                (
                    '_'.join(
                        (
                            "telegram_message_from_farmer_for_support",
                            str(msg.from_user.id),
                            str(msg.message_id),
                            str(msg.date.strftime("%Y-%m-%d_%H-%M-%S"))
                        )
                    ),
                    'jpg'
                )
            )
            path_on_cloud = '.'.join(
                (
                    '/'.join(
                        (
                            "telegram_message_from_farmer_for_support",
                            str(msg.from_user.id),
                            str(msg.message_id),
                            str(index),
                            str(msg.date.strftime("%Y-%m-%d_%H-%M-%S"))
                        )
                    ),
                    'jpg'
                )
            )
            
            await bot.download(
                msg.photo[-1],
                destination=path_local
            )
    
            upload_file(path_local, path_on_cloud)
            if os.path.exists(path_local):
                os.remove(path_local)
            try:
                add_document(
                    {
                        "user_telegram_id": msg.from_user.id,
                        "message_id": messages_id,
                        "message_id_chat": msg.message_id,
                        "image_group_index": index,
                        "type": "image",
                        "time": msg.date,
                        "path_on_cloud": path_on_cloud,
                        "problem": task['problem']
                    }
                    ,
                    "telegram_message_from_farmer_for_support"
                )
                delete_messages.append(msg.message_id)
            except:
                raise print("Upload file on cloud error")
        data = await state.get_data()
        task = data.get(messages[0].from_user.id)
        msg_bot = task["message"]
        res = [j for i in [msg_bot, delete_messages] for j in i]
        task["message"] = res
        await state.update_data({messages[0].from_user.id: task})
        await msg.answer(
            "Save message succesful",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        
@router.message(StateFilter(FSMStatus.chating), F.text)
async def any_text_message(msg: Message, state: FSMContext, bot: Bot):
    firebase_config = get_config()
    data = await state.get_data()
    task = data.get(msg.from_user.id)
    try:
        add_document(
            {
                "user_telegram_id": msg.from_user.id,
                "message_id": msg.message_id,
                "message_id_chat": msg.message_id,
                "type": "text",
                "time": msg.date,
                "text": msg.text,
                "problem": task['problem']
            }
            ,
            "telegram_message_from_farmer_for_support"
        )
        data = await state.get_data()
        task = data.get(msg.from_user.id)
        msg_bot = task["message"]
        msg_bot.append(msg.message_id)
        task["message"] = msg_bot
        await state.update_data({msg.from_user.id: task})
        await msg.answer(
            "Save message succesful",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except:
        print("Add document on cloud error")
    
@router.message(StateFilter(FSMStatus.chating), F.photo)
async def any_image_message(msg: Message, bot: Bot, state: FSMContext):
    '''Save one image with caption'''
    if check_farmer(msg.from_user.id):
        data = await state.get_data()
        task = data.get(msg.from_user.id)
        firebase_config = get_config()
        tz=timezone(firebase_config['timezone'])
        path_local = '.'.join(
            (
                '_'.join(
                    (
                        "telegram_message_from_farmer_for_support",
                        str(msg.from_user.id),
                        str(msg.message_id),
                        str(msg.date)
                    )
                ),
                'jpg'
            )
        )
        path_on_cloud = '.'.join(
            (
                '/'.join(
                    (
                        "telegram_message_from_farmer_for_support",
                        str(msg.from_user.id),
                        str(msg.message_id),
                        str(msg.date.strftime("%Y-%m-%d_%H-%M-%S"))
                    )
                ),
                'jpg'
            )
        )
        await bot.download(
            msg.photo[-1],
            destination=path_local
        )
    
        upload_file(path_local, path_on_cloud)
        if os.path.exists(path_local):
            os.remove(path_local)
        try:
            add_document(
            
                {
                    "user_telegram_id": msg.from_user.id,
                    "message_id": msg.message_id,
                    "message_id_chat": msg.message_id,
                    "type": "image",
                    "time": msg.date,
                    "path_on_cloud": path_on_cloud,
                    "problem": task['problem']
                }
                ,
                "telegram_message_from_farmer_for_support"
            )
        except:
            raise print("Upload file on cloud error")
        try:
            if msg.caption is not None:
                add_document(
                    {
                        "user_telegram_id": msg.from_user.id,
                        "message_id": msg.message_id,
                        "message_id_chat": msg.message_id,
                        "type": "text",
                        "time": msg.date,
                        "text": msg.caption,
                        "problem": task['problem']
                    }
                    ,
                    "telegram_message_from_farmer_for_support"
                )
        except:
            raise print("Add document on cloud error")
        data = await state.get_data()
        task = data.get(msg.from_user.id)
        msg_bot = task["message"]
        msg_bot.append(msg.message_id)
        task["message"] = msg_bot
        await state.update_data({msg.from_user.id: task})
        await msg.answer(
            "Save message succesful",
            parse_mode=ParseMode.MARKDOWN_V2
        )

        
@router.callback_query(StateFilter(FSMStates.wait_menu_click), F.data.startswith("Crop Calendar"))
async def select_calendar(call: types.CallbackQuery, state: FSMContext):
    if check_farmer(call.message.chat.id):
        logging.basicConfig(level=logging.DEBUG)
        names = ["Upcoming", "Outstanding", "Pending", "Overdue", "back"]
        calendar_name = ["Upcoming", "Outstanding", "Pending", "Overdue"]
        buttons = [' '.join((name, '(', str(len(download_information(call.message.chat.id, name))), ')')) if name in calendar_name else name for name in names]
        await call.message.edit_text(
            text = text.calendar,
            reply_markup=create_title_menu([button for button in buttons], [name for name in names]),
            parse_mode=ParseMode.MARKDOWN
        )
        await state.set_state(FSMStates.wait_calendar_name)

@router.callback_query(StateFilter(FSMStatus.support), F.data.startswith('back'))
@router.callback_query(StateFilter(FSMStates.wait_calendar_name), F.data.startswith('back'))
async def back_to_start(call: types.CallbackQuery, state: FSMContext):
    menu = [f'Crop Calendar', f'Agronomics Support']
    buttons = ["Crop Calendar", "Support"]
    await call.message.edit_text(
        text=f'Hi, here are some things I can help with:',
        reply_markup=create_title_menu([name for name in menu], [button for button in buttons]),
        parse_mode=ParseMode.MARKDOWN
    )
    await state.set_state(FSMStates.wait_menu_click)
'''
@router.callback_query(StateFilter(FSMStates.wait_menu_click), F.data.startswith("Crop Calendar"))
async def back_to_start(call: types.CallbackQuery, state: FSMContext):
    try:
        menu = [f'Crop Calendar', f'Agronomics Support']
        buttons = ["Crop Calendar", "Support"]

        await call.message.edit_text(
            text="Chat GPT",
            reply_markup=create_title_menu([name for name in menu], [button for button in buttons]),
            parse_mode=ParseMode.MARKDOWN
        )
    except TelegramBadRequest as ex:
        print(ex.message)
''' 
@router.callback_query(StateFilter(FSMStates.wait_calendar_name))
async def farmer_menu(call: types.CallbackQuery, state: FSMContext):
    name_calendar = call.data
    farmer_id = call.message.chat.id
    farmer_document = DataFramePaginator(download_information(farmer_id, name_calendar), name_calendar=name_calendar)
    if farmer_document.get_DataFrame().empty:
        try:
            msg = f'There are no {name_calendar.lower()} tasks at the moment ✅'
            names = ["Upcoming", "Outstanding", "Pending", "Overdue", "back"]
            calendar_name = ["Upcoming", "Outstanding", "Pending", "Overdue"]
            buttons = [' '.join((name, '(', str(len(download_information(call.message.chat.id, name))), ')')) if name in calendar_name else name for name in names]
            await call.message.edit_text(
                text=msg,
                reply_markup=create_title_menu([button for button in buttons], [name for name in names]),
                parse_mode=ParseMode.MARKDOWN
            )
        except TelegramBadRequest as ex:
            print(ex.message)
    else:
        emojis = {
            "Upcoming": "💤",
            "Outstanding": "🚀",
            "Pending": "📝",
            "Overdue": "🚨",
        }
        msg = f'You are looking at the {name_calendar.lower()} tasks {emojis[name_calendar]}<br/>' + event_brief_information(farmer_document)
        await call.message.edit_text(
            text=msg,
            reply_markup=farmer_document.get_keyboard(info=[farmer_document.get_page_number()]),
            parse_mode=SULGUK_PARSE_MODE
        )
        await state.update_data(
            {
                farmer_id:
                {
                    "name_calendar": name_calendar,
                    "page_number": farmer_document.get_page_number(),
                    "document_id": farmer_document.get_document_id()
                }
            }
        )
        await state.set_state(FSMStates.waiting_for_start_comment)

@router.callback_query(StateFilter(FSMStates.waiting_for_start_comment), F.data.startswith('|'))
async def process_forward_press(call: types.CallbackQuery, state: FSMContext): 
     return 
    
@router.callback_query(StateFilter(FSMStates.waiting_for_start_comment), F.data.startswith('forward'))
async def process_forward_press(call: types.CallbackQuery, state: FSMContext):
    farmer_id = call.message.chat.id
    data = await state.get_data()
    info = data.get(farmer_id)
    name_calendar, page_number, document_id = info['name_calendar'], info['page_number'], info['document_id']
    farmer_document = DataFramePaginator(download_information(farmer_id, name_calendar), name_calendar=name_calendar, page_number = page_number)
    farmer_document.increment_page()
    emojis = {
        "Upcoming": "💤",
        "Outstanding": "🚀",
        "Pending": "📝",
        "Overdue": "🚨",
    }
    msg = f'You are looking at the {name_calendar.lower()} tasks {emojis[name_calendar]}<br/>' + event_brief_information(farmer_document)
    await call.message.edit_text(
        text=msg,
        reply_markup=farmer_document.get_keyboard(
            [
                farmer_id,
                farmer_document.get_page_number()
            ]
        ),
        parse_mode=SULGUK_PARSE_MODE
    )
    info['page_number'] = farmer_document.get_page_number()
    info['document_id'] = farmer_document.get_document_id()
    await state.update_data({farmer_id: info})

@router.callback_query(StateFilter(FSMStates.waiting_for_start_comment), F.data.startswith('backward'))
async def process_backward_press(call: types.CallbackQuery, state: FSMContext):
    farmer_id = call.message.chat.id
    data = await state.get_data()
    info = data.get(farmer_id)
    name_calendar, page_number, document_id = info['name_calendar'], info['page_number'], info['document_id']
    farmer_document = DataFramePaginator(download_information(farmer_id, name_calendar), name_calendar=name_calendar, page_number = page_number)
    farmer_document.decrement_page()
    emojis = {
        "Upcoming": "💤",
        "Outstanding": "🚀",
        "Pending": "📝",
        "Overdue": "🚨",
    }
    msg = f'You are looking at the {name_calendar.lower()} tasks {emojis[name_calendar]}<br/>' + event_brief_information(farmer_document)
    await call.message.edit_text(
        text=msg,
        reply_markup=farmer_document.get_keyboard(
            [
                farmer_id,
                farmer_document.get_page_number()
            ]
        ),
        parse_mode=SULGUK_PARSE_MODE
    )
    info['page_number'] = farmer_document.get_page_number()
    info['document_id'] = farmer_document.get_document_id()
    await state.update_data({farmer_id: info})

@router.callback_query(StateFilter(FSMStates.waiting_for_start_comment), F.data.startswith('back'))
async def process_forward_press(call: types.CallbackQuery, state: FSMContext):
    names = ["Upcoming", "Outstanding", "Pending", "Overdue", "back"]
    calendar_name = ["Upcoming", "Outstanding", "Pending", "Overdue"]
    buttons = [' '.join((name, '(', str(len(download_information(call.message.chat.id, name))), ')')) if name in calendar_name else name for name in names]
    await call.message.edit_text(
        text = text.calendar,
        reply_markup=create_title_menu([button for button in buttons], [name for name in names]),
        parse_mode=ParseMode.MARKDOWN
    )
    await state.set_state(FSMStates.wait_calendar_name)
    
     
@router.callback_query(StateFilter(FSMStates.waiting_more_info), F.data.startswith('back'))
async def back_to_calendar(call: types.CallbackQuery, bot: Bot,  state: FSMContext):
    data = await state.get_data()
    farmer_id = call.message.chat.id
    info = data.get(farmer_id)
    name_calendar, page_number, document_id = info['name_calendar'], info['page_number'], info['document_id']
    if len(download_information(call.message.chat.id, name_calendar)) != 0:
        if page_number > len(download_information(call.message.chat.id, name_calendar)) - 1:
            page_number = len(download_information(call.message.chat.id, name_calendar)) - 1
        farmer_document = DataFramePaginator(download_information(farmer_id, name_calendar), name_calendar, page_number = page_number)
        df = farmer_document.get_DataFrame()
        emojis = {
            "Upcoming": "💤",
            "Outstanding": "🚀",
            "Pending": "📝",
            "Overdue": "🚨",
        }
        msg = f'You are looking at the {name_calendar.lower()} tasks {emojis[name_calendar]}<br/>' + event_brief_information(farmer_document)
        await call.message.edit_text(
            text=msg,
            reply_markup=farmer_document.get_keyboard(
            [
                farmer_id,
                farmer_document.get_page_number()
            ]
            ),
            parse_mode=SULGUK_PARSE_MODE
        )
        await state.set_state(FSMStates.waiting_for_start_comment)
    else:
        names = ["Upcoming", "Outstanding", "Pending", "Overdue", "back"]
        calendar_name = ["Upcoming", "Outstanding", "Pending", "Overdue"]
        buttons = [' '.join((name, '(', str(len(download_information(call.message.chat.id, name))), ')')) if name in calendar_name else name for name in names]
        await call.message.edit_text(
            text = text.calendar,
            reply_markup=create_title_menu([button for button in buttons], [name for name in names]),
            parse_mode=ParseMode.MARKDOWN
        )
        await state.set_state(FSMStates.wait_calendar_name)
    
    
@router.callback_query(StateFilter(FSMStates.waiting_for_start_comment), F.data.startswith('More information'))
async def enter_event(call: types.CallbackQuery, bot: Bot,  state: FSMContext):
    farmer_id = call.message.chat.id
    data = await state.get_data()
    info = data.get(farmer_id)
    name_calendar, page_number, document_id = info['name_calendar'], info['page_number'], info['document_id']
    farmer_document = DataFramePaginator(download_information(farmer_id, name_calendar), name_calendar=name_calendar, page_number = page_number)
    df = farmer_document.get_DataFrame()
    more_info = DataFramePaginator(df[df['document_id'] == document_id], name_calendar=name_calendar)
    emojis = {
        "Upcoming": "💤",
        "Outstanding": "🚀",
        "Pending": "📝",
        "Overdue": "🚨",
    }
    event = event_full_information(more_info)
    task = read_document(document_id, "calendar_events")
    await call.message.edit_text(
        text=event,
        reply_markup=create_title_menu(["back"], ["back"]),
        parse_mode=ParseMode.MARKDOWN
    )
    if task["status"] == "refused":
        agronomist_confirmation = read_collection_with_composite_filter(
            collection = "agronomist_confirmation",
            filters = [
                {
                    "atribut": "calendar_event_id",
                    "op": "==",
                    "value": document_id
                }
            ],
            order = {
                "atribut": "timestamp_submit",
                "desc": True
            }
        )
        if len(agronomist_confirmation) != 0:
            await state.set_state(FSMStates.waiting_for_end_loading_message)
            bot_message = await call.message.answer("Loading comments from the review team")
            agronom_messages_id_on_task = agronomist_confirmation[0]["data"]["messages_id"]
            try:
                agronom_messages = read_collection_with_composite_filter(
                    collection = "message_agronomist_confirmation",
                    filters = [
                        {
                            "atribut": "user_telegram_id",
                            "op": "==",
                            "value": task["agronomist_tg_id"]
                        },
                        {
                            "atribut": "message_id",
                            "op": "in",
                            "value": agronom_messages_id_on_task
                        }
                    ]
                )
                agronom_messages_data = [message["data"] for message in agronom_messages]
                df = pd.DataFrame.from_dict(agronom_messages_data)
                df_text = df[df["type"] == "text"]
                df_image = df[df["type"] == "image"]
               
                if len(df_text) != 0 and len(df_image) != 0:
                    df_text = df_text.sort_values(["message_id_chat"])
                    text_messages = list(df_text["text"])
                    caption = 'Comments from the review team:\n' + '\n\n'.join(text_messages)
                    album_builder = MediaGroupBuilder(caption=caption)
                    df_image = df_image.sort_values(["message_id_chat"])
                    local_paths = []
              
                    for i in range(len(df_image)):
                        if i > 9:
                            break
                        path_on_cloud = df_image[i: i + 1]["path_on_cloud"].item()
                        path_local = '_'.join(("message_for_farmer", str(i), str(path_on_cloud).replace('/', '_')))
                       
                        try:
                            download_file(path_on_cloud, path_local)
                            album_builder.add(
                                type="photo",
                                media=FSInputFile(path_local)
                            )
                            local_paths.append(path_local)
                        except:
                            print("Error send to {call.message.chat.id}: {path_on_cloud}")
                   
                    await call.message.answer_media_group(
                        media=album_builder.build(),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    for path_local in local_paths:
                        if os.path.exists(path_local):
                            os.remove(path_local)
                elif len(df_text) == 0 and len(df_image) != 0:
                    album_builder = MediaGroupBuilder()
                    df_image = df_image.sort_values(["message_id_chat"])
                    local_paths = []
                    for i in range(len(df_image)):
                        if i > 9:
                            break
                        path_on_cloud = df_image[i: i + 1]["path_on_cloud"].item()
                        path_local = '_'.join(("message_for_farmer", str(i), str(path_on_cloud).replace('/', '_')))
                        try:
                            download_file(path_on_cloud, path_local)
                            album_builder.add(
                                type="photo",
                                media=FSInputFile(path_local)
                            )
                            local_paths.append(path_local)
                        except:
                            print("Error send to {call.message.chat.id}: {path_on_cloud}")
                    await call.message.answer_media_group(
                        media=album_builder.build(),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    for path_local in local_paths:
                        if os.path.exists(path_local):
                            os.remove(path_local)
                elif len(df_text) != 0 and len(df_image) == 0:
                    df_text = df_text.sort_values(["message_id_chat"])
                    text_messages = list(df_text["text"])
                    caption = 'Comments from the review team:\n' + '\n\n'.join(text_messages)
                    await call.message.answer(
                        caption,
                        reply_markup=create_title_menu(["Got it!"], ["Got it!"]),
                        parse_mode=ParseMode.MARKDOWN
                    )
                await bot_message.delete()
            except:
                print(f'Problem send refused for event {document_id} to farmer with {farmer_id}')
    await state.set_state(FSMStates.waiting_more_info)

    
@router.callback_query(StateFilter(FSMStates.waiting_for_start_comment), F.data.startswith('respond'))
async def enter_event(call: types.CallbackQuery, state: FSMContext):
    farmer_id = call.message.chat.id
    data = await state.get_data()
    info = data.get(farmer_id)
    name_calendar, page_number, document_id = info['name_calendar'], info['page_number'], info['document_id']
    farmer_document = DataFramePaginator(download_information(farmer_id, name_calendar), name_calendar, page_number = page_number)
    
    emojis = {
        "Upcoming": "💤",
        "Outstanding": "🚀",
        "Pending": "📝",
        "Overdue": "🚨",
    }
    task_info = event_full_information(farmer_document)
    event = f'You are looking at the {name_calendar.lower()} tasks {emojis[name_calendar]}<br/>' + task_info
    doc = read_document(document_id, "calendar_events")
    if doc["status"] in ["farmer_response", "completed", "notified_agronomist", "accepted"]:
        try:
            msg = '<br/><br/>'.join((event, "*You have already responded to this event.*"))
            await call.message.edit_text(
                text=msg,
                reply_markup=farmer_document.get_keyboard(
                [
                    farmer_id,
                    farmer_document.get_page_number()
                ]
                ),
                parse_mode=SULGUK_PARSE_MODE
            )
        except TelegramBadRequest as ex:
            print(ex.message)
        return
    if doc["type"] == "task_without_confirmation":
        await call.message.edit_text(
            text = event_without_confirm(farmer_document),
            reply_markup=create_title_menu(["yes", "no" , "back"], ["yes", "no", "back"]),
            parse_mode=ParseMode.MARKDOWN
        )
        await state.set_state(FSMStates.waiting_for_end_confirm)
    else:
        firebase_config = get_config()
        tz = timezone(firebase_config['timezone'])
        time = datetime.now(tz=tz)


        add_document(
            {
                "calendar_event_id": document_id,
                "farmer_tg_id": farmer_id,
                "timestamp_creates": time,
                "messages_id": [],
            },
            "farmer_response_buffer"
        )
        responses = read_collection_with_composite_filter(
            collection = "farmer_response_buffer",
            filters = [
                {
                    "atribut": "calendar_event_id",
                    "op": "==",
                    "value": document_id
                }
            ],
            order = {
                "atribut": "timestamp_creates",
                "desc": True
            }
        )
        
        task_message  = await call.message.answer(
            text=task_info,
            parse_mode=ParseMode.MARKDOWN
        )
        type_message = await call.message.answer(
            text="Please type in any supporting information you can provide on this task!",
            reply_markup=create_title_menu(["submit", "back"], ["submit", "back"]),
            parse_mode=ParseMode.MARKDOWN
        )
        await call.message.delete()
        await state.update_data(
            {
                farmer_id:
                {
                    "count_loading": 0,
                    "id": responses[0]["document_id"],
                    "name_calendar": name_calendar,
                    "page_number": page_number,
                    "document_id": document_id,
                    "message": [task_message.message_id, type_message.message_id]
                    
                }
            }
        )
        await state.set_state(FSMStates.waiting_for_end_comment)
    
@router.callback_query(StateFilter(FSMStates.waiting_for_end_confirm))
async def confirm(call: types.CallbackQuery, bot: Bot, state: FSMContext):
    try:
        button = call.data

        if button == "yes" or button == "no":
            farmer_id = call.message.chat.id
            data = await state.get_data()
            info = data.get(farmer_id)
            name_calendar, page_number, document_id = info['name_calendar'], info['page_number'], info['document_id']
            firebase_config = get_config()
            tz = timezone(firebase_config['timezone'])
            time = datetime.now(tz=tz)
            add_document(
                {
                    "calendar_event_id": document_id,
                    "farmer_tg_id": farmer_id,
                    "timestamp_creates": time,
                    "timestamp_submit": time,
                    "status": button,
                    "messages_id": [],
                },
                "farmer_response"
            )
            update_document(document_id, {"status": "completed"}, "calendar_events")
            
            message_thank = await call.message.answer(
                text = "Thank you, information was submitted successfully!",
                parse_mode=ParseMode.MARKDOWN
            )
        data = await state.get_data()
        info = data.get(farmer_id)
        name_calendar, page_number, document_id = info['name_calendar'], info['page_number'], info['document_id']
        if len(download_information(call.message.chat.id, name_calendar)) != 0:
            if page_number > len(download_information(call.message.chat.id, name_calendar)) - 1:
                page_number = len(download_information(call.message.chat.id, name_calendar)) - 1
            farmer_document = DataFramePaginator(download_information(farmer_id, name_calendar), name_calendar, page_number = page_number)
            df = farmer_document.get_DataFrame()
            emojis = {
                "Upcoming": "💤",
                "Outstanding": "🚀",
                "Pending": "📝",
                "Overdue": "🚨",
            }
            msg = f'You are looking at the {name_calendar.lower()} tasks {emojis[name_calendar]}<br/>' + event_brief_information(farmer_document)
            await call.message.answer(
                text=msg,
                reply_markup=farmer_document.get_keyboard(
                [
                    farmer_id,
                    farmer_document.get_page_number()
                ]
                ),
                parse_mode=SULGUK_PARSE_MODE
            )
            await state.set_state(FSMStates.waiting_for_start_comment)
        else:
            names = ["Upcoming", "Outstanding", "Pending", "Overdue", "back"]
            calendar_name = ["Upcoming", "Outstanding", "Pending", "Overdue"]
            buttons = [' '.join((name, '(', str(len(download_information(call.message.chat.id, name))), ')')) if name in calendar_name else name for name in names]
            await call.message.answer(
                text = text.calendar,
                reply_markup=create_title_menu([button for button in buttons], [name for name in names]),
                parse_mode=ParseMode.MARKDOWN
            )
            await state.set_state(FSMStates.wait_calendar_name)
        try:
            await call.message.delete()
        except:
            print(f'Error clean {call.message.chat.id} message_id: {message_id}')
    except:
        names = ["Upcoming", "Outstanding", "Pending", "Overdue", "back"]
        calendar_name = ["Upcoming", "Outstanding", "Pending", "Overdue"]
        buttons = [' '.join((name, '(', str(len(download_information(call.message.chat.id, name))), ')')) if name in calendar_name else name for name in names]
        await call.message.edit_text(
            text = text.calendar,
            reply_markup=create_title_menu([button for button in buttons], [name for name in names]),
            parse_mode=ParseMode.MARKDOWN
        )
        await state.set_state(FSMStates.wait_calendar_name)
    await asyncio.sleep(3)
    try:
        await message_thank.delete()
    except:
        print(f'Error clean {call.message.chat.id}')

@router.callback_query(StateFilter(FSMStates.waiting_for_end_comment), F.data.startswith('back'))
async def go_to_start(call: types.CallbackQuery, bot: Bot, state: FSMContext):
    '''Go to start. Cancel comment.
    Args:
        message:
            message from user
        state:
            state for bot
    '''
    data = await state.get_data()
    try:
        data = await state.get_data()
        task = data.get(call.message.chat.id)
        if task["count_loading"] > 0:
            message_loading = await call.message.answer("Wait for previous messages to finish loading")
            msg_bot = task["message"]
            msg_bot.append(message_loading.message_id)
            task["message"] = msg_bot
            await state.update_data(
                {
                call.message.chat.id: task
                }
            )
            return
    except:
        print(f'state no contain {message.from_user.id}')
        
    try:
        await state.set_state(FSMStates.waiting_for_end_cancel_comment)
        confirmations = read_collection_with_composite_filter(
            collection = "farmer_response_buffer",
            filters = [
                {
                    "atribut": "farmer_tg_id",
                    "op": "==",
                    "value": call.message.chat.id
                }
            ],
            order = {
                "atribut": "timestamp_creates",
                "desc": True
            }
        )
        
        if len(confirmations):
            confirmation = confirmations[0]
            messages_id = confirmation["data"]["messages_id"]
            
            if len(messages_id):
                bot_message = await call.message.answer("Wait delete messages")
            
            for message_id in messages_id:
                farmer_messages = read_collection_with_composite_filter(
                    filters = [
                        {
                            "atribut": "user_telegram_id",
                            "op": "==",
                            "value": call.message.chat.id
                        },
                        {
                            "atribut": "message_id",
                            "op": "==",
                            "value": message_id
                        }
                    ],
                    collection = "message_farmer_response"
                )
                for farmer_message in farmer_messages:
                    if farmer_message["data"]["type"] == "image":
                        path_local = farmer_message["data"]["path_on_cloud"].replace("/", "_")
                        if os.path.exists(path_local):
                            os.remove(path_local)
                        delete_document(farmer_message["document_id"], collection = "message_farmer_response")
                    elif farmer_message["data"]["type"] == "text":
                        delete_document(farmer_message["document_id"], collection = "message_farmer_response")
                    try:
                        await bot.delete_message(call.message.chat.id, farmer_message["data"]["message_id_chat"])
                    except:
                        print(f'Error clean {call.message.chat.id} message_id: {farmer_message["data"]["message_id_chat"]}')
            if len(messages_id): await bot_message.delete()
 
            delete_document(confirmation["document_id"], collection = "farmer_response_buffer")
        info = data.get(call.message.chat.id)       

        farmer_id = call.message.chat.id
        data = await state.get_data()
        info = data.get(farmer_id)
        name_calendar, page_number, document_id = info['name_calendar'], info['page_number'], info['document_id']
        if len(download_information(call.message.chat.id, name_calendar)) != 0:
            if page_number > len(download_information(call.message.chat.id, name_calendar)) - 1:
                page_number = len(download_information(call.message.chat.id, name_calendar)) - 1
            farmer_document = DataFramePaginator(download_information(farmer_id, name_calendar), name_calendar, page_number = page_number)
            df = farmer_document.get_DataFrame()
            emojis = {
                "Upcoming": "💤",
                "Outstanding": "🚀",
                "Pending": "📝",
                "Overdue": "🚨",
            }
            msg = f'You are looking at the {name_calendar.lower()} tasks {emojis[name_calendar]}<br/>' + event_brief_information(farmer_document)
            await call.message.answer(
                text=msg,
                reply_markup=farmer_document.get_keyboard(
                [
                    farmer_id,
                    farmer_document.get_page_number()
                ]
                ),
                parse_mode=SULGUK_PARSE_MODE
            )
            for  message_id in info["message"]:
                try:
                    await bot.delete_message(call.message.chat.id, message_id)
                except:
                    print(f'Error clean {call.message.chat.id} message_id: {message_id}')
            await state.set_state(FSMStates.waiting_for_start_comment)
        else:
            names = ["Upcoming", "Outstanding", "Pending", "Overdue", "back"]
            calendar_name = ["Upcoming", "Outstanding", "Pending", "Overdue"]
            buttons = [' '.join((name, '(', str(len(download_information(call.message.chat.id, name))), ')')) if name in calendar_name else name for name in names]
            await call.message.answer(
                text = text.calendar,
                reply_markup=create_title_menu([button for button in buttons], [name for name in names]),
                parse_mode=ParseMode.MARKDOWN
            )
            for  message_id in info["message"]:
                try:
                    await bot.delete_message(call.message.chat.id, message_id)
                except:
                    print(f'Error clean {call.message.chat.id} message_id: {message_id}')
            await state.set_state(FSMStates.wait_calendar_name)
    except:
        names = ["Upcoming", "Outstanding", "Pending", "Overdue", "back"]
        calendar_name = ["Upcoming", "Outstanding", "Pending", "Overdue"]
        buttons = [' '.join((name, '(', str(len(download_information(call.message.chat.id, name))), ')')) if name in calendar_name else name for name in names]
        await call.message.answer(
            text = text.calendar,
            reply_markup=create_title_menu([button for button in buttons], [name for name in names]),
            parse_mode=ParseMode.MARKDOWN
        )
        await state.set_state(FSMStates.wait_calendar_name)





@router.callback_query(StateFilter(FSMStates.waiting_for_end_comment), F.data.startswith('submit'))
async def submit_response(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task = data.get(call.message.chat.id)
    if task["count_loading"] > 0:
        message_loading = await call.message.answer("Wait for previous messages to finish loading")
        msg_bot = task["message"]
        msg_bot.append(message_loading.message_id)
        task["message"] = msg_bot
        await state.update_data(
            {
                call.message.chat.id: task
            }
        )
        return


    document_id = task["id"]
    confirmation = read_document(document_id, collection = "farmer_response_buffer")
    messages_id = confirmation["messages_id"]
    if len(messages_id) == 0:
        bot_message = await call.message.answer("You didn't write message")
        msg_bot = task["message"]
        msg_bot.append(bot_message.message_id)
        task["message"] = msg_bot
        await state.update_data(
            {
                call.message.chat.id: task
            }
        )
        return
        
    farmer_messages = read_collection_with_composite_filter(
        filters = [
            {
                "atribut": "user_telegram_id",
                "op": "==",
                "value": call.message.chat.id
            },
            {
                "atribut": "message_id",
                "op": "in",
                "value": messages_id
            },
            {
                "atribut": "type",
                "op": "==",
                "value": "image"
            }
        ],
        collection = "message_farmer_response"
    )
    if len(farmer_messages) == 0:
        await call.message.edit_text(
            text="Please type in any supporting information you can provide on this task!",
            reply_markup=None,
            parse_mode=ParseMode.MARKDOWN
        )
        message_provide = await call.message.answer(
            text="Please provide supporting visuals to confirm the completion of the task, otherwise type in you reasons for not having the data",
            reply_markup=create_title_menu(["submit", "back"], ["Trust", "back"]),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await call.message.edit_text(
            text="Please type in any supporting information you can provide on this task!",
            reply_markup=None,
            parse_mode=ParseMode.MARKDOWN
        )
        message_provide = await call.message.answer(
            text = "Press Submit, otherwise press Back to restart the submission process.",
            reply_markup=create_title_menu(["submit", "back"], ["Trust", "back"]),
            parse_mode=ParseMode.MARKDOWN
        )
    data = await state.get_data()
    task = data.get(call.message.chat.id)
    msg_bot = task["message"]
    msg_bot.append(message_provide.message_id)
    task["message"] = msg_bot
    await state.update_data(
    {  
        call.message.chat.id: task
    }
    )

@router.callback_query(StateFilter(FSMStates.waiting_for_end_comment), F.data.startswith('Trust'))
async def trust(call: types.CallbackQuery, bot: Bot, state: FSMContext):
    try:
        data = await state.get_data()
        task = data.get(call.message.chat.id)
        if task["count_loading"] > 0:
            message_loading = await call.message.answer("Wait for previous messages to finish loading")
            msg_bot = task["message"]
            msg_bot.append(message_loading.message_id)
            task["message"] = msg_bot
            await state.update_data(
                {
                call.message.chat.id: task
                }
            )
            return
        await state.set_state(FSMStates.waiting_for_end_loading_message)
        document_id = task["id"]
        confirmation = read_document(document_id, collection = "farmer_response_buffer")
        messages_id = confirmation["messages_id"]
        for message_id in messages_id:
            farmer_messages = read_collection_with_composite_filter(
                filters = [
                    {
                        "atribut": "user_telegram_id",
                        "op": "==",
                        "value": call.message.chat.id
                    },
                    {
                        "atribut": "message_id",
                        "op": "==",
                        "value": message_id
                    }
                ],
                collection = "message_farmer_response"
            )
            for farmer_message in farmer_messages:
                if farmer_message["data"]["type"] == "image":
                    path_local = farmer_message["data"]["path_on_cloud"].replace("/", "_")
                    
                    if os.path.exists(path_local):
                        upload_file(path_local, farmer_message["data"]["path_on_cloud"])
                        os.remove(path_local)
                try:
                    await bot.delete_message(call.message.chat.id, farmer_message["data"]["message_id_chat"])
                except:
                    print(f'Error clean {call.message.chat.id} message_id: {farmer_message["data"]["message_id_chat"]}')
        calendar_event_id = confirmation["calendar_event_id"]
        update_document(calendar_event_id, {"status": "farmer_response"}, "calendar_events")
        delete_document(document_id, "farmer_response_buffer")
        firebase_config = get_config()
        tz=timezone(firebase_config['timezone'])
        time = datetime.now(tz=tz)
        confirmation["timestamp_submit"] = time
        add_document(confirmation, "farmer_response")

        message_thank = await call.message.answer(
            text = "Thank you, information was submitted successfully!",
            parse_mode=ParseMode.MARKDOWN
        )
        for  message_id in task["message"]:
            try:
                await bot.delete_message(call.message.chat.id, message_id)
            except:
                 print(f'Error clean {call.message.chat.id} message_id: {message_id}')
        farmer_id = call.message.chat.id
        data = await state.get_data()
        info = data.get(farmer_id)
        name_calendar, page_number, document_id = info['name_calendar'], info['page_number'], info['document_id']
        if len(download_information(call.message.chat.id, name_calendar)) != 0:
            if page_number > len(download_information(call.message.chat.id, name_calendar)) - 1:
                page_number = len(download_information(call.message.chat.id, name_calendar)) - 1
            farmer_document = DataFramePaginator(download_information(farmer_id, name_calendar), name_calendar, page_number = page_number)
            df = farmer_document.get_DataFrame()
            emojis = {
                "Upcoming": "💤",
                "Outstanding": "🚀",
                "Pending": "📝",
                "Overdue": "🚨",
            }
            msg = f'You are looking at the {name_calendar.lower()} tasks {emojis[name_calendar]}<br/>' + event_brief_information(farmer_document)
            await call.message.answer(
                text=msg,
                reply_markup=farmer_document.get_keyboard(
                [
                    farmer_id,
                    farmer_document.get_page_number()
                ]
                ),
                parse_mode=SULGUK_PARSE_MODE
            )
            await state.set_state(FSMStates.waiting_for_start_comment)
        else:
            names = ["Upcoming", "Outstanding", "Pending", "Overdue", "back"]
            calendar_name = ["Upcoming", "Outstanding", "Pending", "Overdue"]
            buttons = [' '.join((name, '(', str(len(download_information(call.message.chat.id, name))), ')')) if name in calendar_name else name for name in names]
            await call.message.answer(
                text = text.calendar,
                reply_markup=create_title_menu([button for button in buttons], [name for name in names]),
                parse_mode=ParseMode.MARKDOWN
            )
            await state.set_state(FSMStates.wait_calendar_name)
    except:
        names = ["Upcoming", "Outstanding", "Pending", "Overdue", "back"]
        calendar_name = ["Upcoming", "Outstanding", "Pending", "Overdue"]
        buttons = [' '.join((name, '(', str(len(download_information(call.message.chat.id, name))), ')')) if name in calendar_name else name for name in names]
        await call.message.answer(
            text = text.calendar,
            reply_markup=create_title_menu([button for button in buttons], [name for name in names]),
            parse_mode=ParseMode.MARKDOWN
        )
        await state.set_state(FSMStates.wait_calendar_name)
    await asyncio.sleep(3)
    try:
        await message_thank.delete()
    except:
        print(f'Error clean {call.message.chat.id}')

@router.message(StateFilter(FSMStates.waiting_for_end_comment), F.media_group_id, F.content_type.in_({'photo'}))
@media_group_handler
async def album_handler(messages: List[types.Message], bot: Bot, state: FSMContext):
    '''Save group of images with caption'''
    if True:
        data = await state.get_data()
        task = data.get(messages[0].from_user.id)
        task["count_loading"] += 1
        await state.update_data({messages[0].from_user.id: task})
        document_id = task["id"]
        messages_id = messages[0].message_id
        firebase_config = get_config()
        tz=timezone(firebase_config['timezone'])
        time = datetime.now(tz=tz)
        try:
            if messages[0].caption is not None:
                add_document(
                    {
                        "user_telegram_id": messages[0].from_user.id,
                        "message_id": messages_id,
                        "message_id_chat": messages_id,
                        "type": "text",
                        "time": time,
                        "text": messages[0].caption
                    }
                    ,
                    "message_farmer_response"
                )
        except:
            print("Add document on cloud error")
        for index, msg in enumerate(messages):
            path_local = '.'.join(('_'.join(("message_farmer_response", str(msg.from_user.id), str(messages_id), str(index), time.strftime("%Y-%m-%d_%H-%M-%S")
)), 'jpg'))
            path_on_cloud = '.'.join(('/'.join(("message_farmer_response", str(msg.from_user.id), str(messages_id), str(index), time.strftime("%Y-%m-%d_%H-%M-%S")
)), 'jpg'))
            await bot.download(
                msg.photo[-1],
                destination=path_local
            )
            try:
                add_document(
                    {
                        "user_telegram_id": msg.from_user.id,
                        "message_id": messages_id,
                        "message_id_chat": msg.message_id,
                        "image_group_index": index,
                        "type": "image",
                        "time": time,
                        "path_on_cloud": path_on_cloud
                    }
                    ,
                    "message_farmer_response"
                )
            except:
                print("Upload file on cloud error")
        data = await state.get_data()
        task = data.get(messages[0].from_user.id)
        task["count_loading"] -= 1
        await state.update_data({messages[0].from_user.id: task})
        update_document_array(
            document_id = document_id,
            array_name = "messages_id",
            collection = "farmer_response_buffer",
            value = [messages_id]
        )

@router.message(StateFilter(FSMStates.waiting_for_end_comment), F.text)
async def any_text_message(message: Message, state: FSMContext):
    '''Save text message'''
    if True:
        data = await state.get_data()
        task = data.get(message.from_user.id)
        task["count_loading"] += 1
        await state.update_data({message.from_user.id: task})
        document_id = task["id"]
        firebase_config = get_config()
        tz=timezone(firebase_config['timezone'])
        time = datetime.now(tz=tz)
        try:
            add_document(
                
                {
                    "user_telegram_id": message.from_user.id,
                    "message_id": message.message_id,
                    "message_id_chat": message.message_id,
                    "type": "text",
                    "time": time,
                    "text": message.text
                }
                ,
                "message_farmer_response"
            )
        except:
            print("Add document on cloud error")
        data = await state.get_data()
        task = data.get(message.from_user.id)
        task["count_loading"] -= 1
        await state.update_data({message.from_user.id: task})
        update_document_array(
            document_id = document_id,
            array_name = "messages_id",
            collection = "farmer_response_buffer",
            value = [message.message_id]
        )

@router.message(StateFilter(FSMStates.waiting_for_end_comment), F.photo)
async def any_image_message(message: Message, bot: Bot, state: FSMContext):
    '''Save one image with caption'''
    if True:
        data = await state.get_data()
        task = data.get(message.from_user.id)
        task["count_loading"] += 1
        await state.update_data({message.from_user.id: task})
        document_id = task["id"]
        firebase_config = get_config()
        tz=timezone(firebase_config['timezone'])
        time = datetime.now(tz=tz)
        path_local = '.'.join(('_'.join(("message_farmer_response", str(message.from_user.id), str(message.message_id), time.strftime("%Y-%m-%d_%H-%M-%S"))), 'jpg'))
        path_on_cloud = '.'.join(('/'.join(("message_farmer_response", str(message.from_user.id), str(message.message_id), time.strftime("%Y-%m-%d_%H-%M-%S"))), 'jpg'))
        await bot.download(
            message.photo[-1],
            destination=path_local
        )
        try:
            add_document(
            
                {
                    "user_telegram_id": message.from_user.id,
                    "message_id": message.message_id,
                    "message_id_chat": message.message_id,
                    "type": "image",
                    "time": time,
                    "path_on_cloud": path_on_cloud
                }
                ,
                "message_farmer_response"
            )
        except:
            print("Upload file on cloud error")
        try:
            if message.caption is not None:
                add_document(
                    {
                        "user_telegram_id": message.from_user.id,
                        "message_id": message.message_id,
                        "message_id_chat": message.message_id,
                        "type": "text",
                        "time": time,
                        "text": message.caption
                    }
                    ,
                    "message_farmer_response"
                )
        except:
            print("Add document on cloud error")
        data = await state.get_data()
        task = data.get(message.from_user.id)
        task["count_loading"] -= 1
        await state.update_data({message.from_user.id: task})
        document_id = task["id"]
        update_document_array(
            document_id = document_id,
            array_name = "messages_id",
            collection = "farmer_response_buffer",
            value = [message.message_id]
        )
