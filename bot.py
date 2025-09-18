import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from telegram.ext import CommandHandler
from telegram import ReplyKeyboardMarkup, KeyboardButton
import aiohttp
import random

load_dotenv()

token = os.getenv('TOKEN')
token_weather = os.getenv('TOKEN_WEATHER')
PROXY_URL = 'http://proxy.server:3128'

breeds_list = []

# Возвращает информацию о пользователе
def get_user_info(update: Update):
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id
    message = update.effective_message
    timestamp = int(message.date.timestamp())
    first_name = user.first_name or ''
    last_name = user.last_name or ''
    full_name = f'{first_name} {last_name}'.strip()
    ava_str = user.id * timestamp # Получается случайное число путём произведенияid пользователя и времени
    ava_url = f'https://robohash.org/{ava_str}?set=set1' # Был изменён параметр set, теперь генерируются аватарки роботов
    return chat_id, first_name, full_name, ava_url, user_id

# Обрабатывает любой текст, написанный пользователем
async def say_hi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_info = get_user_info(update)
    text = update.message.text
    if text == 'Фото котика':
        await send_cat(update, context)
    elif text == 'Фото собаки':
        await specify_dog(update, context)
    elif text == 'Сгенери аватар':
        await context.bot.send_photo(chat_id=user_info[0], photo=user_info[3])
    elif text == 'Мой ID':
        await context.bot.send_message(chat_id=user_info[0], text=f'Твой ID: {user_info[4]}')
    elif text == 'Погода сегодня':
        await request_location(update, context)
    elif text == 'Случайная порода':
        await send_random_dog(update, context)
    elif text in breeds_list:
        await send_dog(update, context, text)
    elif text == 'Главное меню':
        await wake_up(update, context,)
    else:
        await context.bot.send_message(chat_id=user_info[0], text=f'{user_info[1]}, как твои дела?')

# Срабатывает, когда пользователь начинает общаться с ботом или пишет в чат /start
async def wake_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_info = get_user_info(update)
    button = ReplyKeyboardMarkup([
        ['Фото котика', 'Фото собаки'],
        ['Мой ID', 'Сгенери аватар'],
        ['Погода сегодня']
    ], resize_keyboard=True)
    await context.bot.send_message(
    chat_id=user_info[0],
    text=f'Привет {user_info[2]}, спасибо, что присоединился!',
    reply_markup=button)

# Отправляется запрос на получение данных о локации
async def request_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_info = get_user_info(update)
    location_keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton('Отправить координаты 📍', request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await context.bot.send_message(chat_id=user_info[0], text='Пожалуйста, поделитесь своей геолокацией:',
    reply_markup=location_keyboard
    )

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location = update.message.location
    latitude = location.latitude
    longitude = location.longitude
    context.user_data['location'] = (latitude, longitude)
    weather_report = await get_weather(latitude, longitude)
    await update.message.reply_text(weather_report)
    main_menu = ReplyKeyboardMarkup([
        ['Фото котика', 'Фото собаки'],
        ['Мой ID', 'Сгенери аватар'],
        ['Погода сегодня']
    ], resize_keyboard=True)
    await update.message.reply_text('👌', reply_markup=main_menu)

# Генерирование текста сообщения о погоде
async def get_weather(lat: float, lon: float) -> str:
    url=f'https://api.openweathermap.org/data/2.5/weather?APPID={token_weather}&lang=ru&units=metric&lat={lat}&lon={lon}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url, proxy=PROXY_URL) as resp:
            if resp.status != 200:
                return 'Ошибка при получении данных о погоде'
            data = await resp.json()
    city = data.get('name', 'Неизвестное место')
    weather = data['weather'][0]['description']
    temp = data['main']['temp']
    feels_like = data['main']['feels_like']
    wind_speed = data['wind']['speed']
    if wind_speed < 5:
        wind_recom = '🌤 Погода хорошая, ветра почти нет'
    elif wind_speed < 10:
        wind_recom = '🌫 На улице ветрено, оденьтесь чуть теплее'
    elif wind_speed < 20:
        wind_recom = '🌬 Ветер очень сильный, будьте осторожны, выходя из дома'
    else:
        wind_recom = '🌪 На улице шторм, на улицу лучше не выходить'
    return (
        f'Сейчас в {city} {weather}\n'
        f'🌡 Температура: {temp}°C (ощущается как {feels_like}°C)\n'
        f'💨 Ветер: {wind_speed} м/с\n'
        f'{wind_recom}'
    )

# Отправляет случайную аватарку
async def send_ava(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_info = get_user_info(update)
    await context.bot.send_photo(chat_id=user_info[0], photo=user_info[3])

# Отправляет картинку кота
async def send_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_info = get_user_info(update)
    url = f'https://cataas.com/cat/says/{user_info[1]}?json=true' # Указывается имя пользователя, которое потом добавляется к фото
    async with aiohttp.ClientSession() as session:
        async with session.get(url, proxy=PROXY_URL) as resp:
            if resp.status != 200:
                context.bot.send_message(chat_id=user_info[0], text='Ошибка в получении картинки кота')
                return
            data = await resp.json()
    picture_url = data.get('url')
    await context.bot.send_photo(chat_id=user_info[0], photo=picture_url)

# Уточняет породу собаки
async def specify_dog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_info = get_user_info(update)

    await get_dog_breeds()
    br = random.sample(breeds_list, 6)

    button = ReplyKeyboardMarkup([
        [br[0], br[1]],
        [br[2], br[3]],
        [br[4], br[5]],
        ['Случайная порода', 'Главное меню']
    ], resize_keyboard=True)
    await context.bot.send_message(
        chat_id=user_info[0],
        text=f'Выберите породу собаки',
        reply_markup=button
    )

# Получает список всех пород собак
async def get_dog_breeds():
    async with aiohttp.ClientSession() as session:
        async with session.get('https://dog.ceo/api/breeds/list/all', proxy=PROXY_URL) as response:
            data = await response.json()
    for breed_group, sub_breeds in data["message"].items():
        if len(sub_breeds) > 0:
            for sub_breed in sub_breeds:
                breeds_list.append(f"{breed_group}/{sub_breed}")
        else:
            breeds_list.append(breed_group)
    print(breeds_list)

# Отправляет случайную картинку конкретной породы собаки
async def send_dog(update: Update, context: ContextTypes.DEFAULT_TYPE, breed: str):
    user_info = get_user_info(update)
    url = f'https://dog.ceo/api/breed/{breed}/images/random'
    async with aiohttp.ClientSession() as session:
        async with session.get(url, proxy=PROXY_URL) as resp:
            if resp.status != 200:
                context.bot.send_message(chat_id=user_info[0], text='Ошибка в получении картинки собаки')
                return
            data = await resp.json()
    picture_url = data.get('message')
    await context.bot.send_photo(chat_id=user_info[0], photo=picture_url)

# Отправляет картинку случайной породы собаки
async def send_random_dog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_info = get_user_info(update)
    url = f'https://dog.ceo/api/breeds/image/random'
    async with aiohttp.ClientSession() as session:
        async with session.get(url, proxy=PROXY_URL) as resp:
            if resp.status != 200:
                context.bot.send_message(chat_id=user_info[0], text='Ошибка в получении картинки собаки')
                return
            data = await resp.json()
    picture_url = data.get('message')
    await context.bot.send_photo(chat_id=user_info[0], photo=picture_url)

def run_bot():
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler('start', wake_up))
    app.add_handler(MessageHandler(filters.TEXT, say_hi))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.run_polling() # poll_interval=5.0