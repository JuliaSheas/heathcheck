import sqlite3
import sys
import schedule
import telebot
from telebot import types
import threading
import time
from datetime import datetime

bot = telebot.TeleBot("BOT ID")
ADMIN_ID = ADMIN ID

def update_database_schema():
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA table_info(temp_id)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    if 'name' not in column_names:
        cursor.execute("""
            ALTER TABLE temp_id
            ADD COLUMN name TEXT;
        """)
        connect.commit()
    connect.close()

update_database_schema()

def create_tables():
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS login_id (
                        id INTEGER PRIMARY KEY,
                        name TEXT,
                        room TEXT)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS temp_id (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        date TEXT,
                        temp REAL)""")
    connect.commit()
    connect.close()

create_tables()

def job():
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    cursor.execute("SELECT id FROM login_id")
    rows = cursor.fetchall()
    for row in rows:
        user_id = row[0]
        if user_id != ADMIN_ID:  # Виключаємо адміністратора з розсилки
            bot.send_message(user_id, "Нагадування про щоденне опитування\nПройти /poll")
            print(f"Нагадування про опитування надіслано користувачу з ID: {user_id}")
    connect.close()


schedule.every().day.at("15:46").do(job)

def go():
    while True:
        schedule.run_pending()
        time.sleep(1)

t = threading.Thread(target=go, name="SchedulerThread")
t.start()

def welcome_new_user(message):
    bot.send_message(message.chat.id, "Вітаємо! Щоб продовжити, будь ласка, вкажіть своє прізвище:")
    bot.register_next_step_handler(message, register_lastname)

def register_lastname(message):
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    cursor.execute("INSERT INTO login_id (id, name) VALUES (?, ?);", (message.chat.id, message.text))
    connect.commit()
    bot.send_message(message.chat.id, "Тепер вкажіть номер своєї кімнати:")
    bot.register_next_step_handler(message, register_room)
    connect.close()
def is_registered(user_id):
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    cursor.execute("SELECT id FROM login_id WHERE id = ?", (user_id,))
    data = cursor.fetchone()
    connect.close()
    return data is not None

def register_room(message):
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    cursor.execute("UPDATE login_id SET room = ? WHERE id = ?;", (message.text, message.chat.id))
    connect.commit()
    bot.send_message(message.chat.id, "Дякуємо! Ваші дані збережено.")
    bot.send_message(message.chat.id,  "Даний бот створений для контролю стану здоров`я мешканців гуртожитку.\n\nДоступні команди:\n\n/poll - пройти опитування\n/rename - змінити прізвище/номер кімнати\n/mytemp - статистика температури")
    connect.close()

@bot.message_handler(commands=['start'])
def st(message):
    if message.chat.id == ADMIN_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_broadcast = types.KeyboardButton("Розіслати повідомлення")
        item_force_poll = types.KeyboardButton("Примусове опитування")
        markup.add(item_broadcast, item_force_poll)
        bot.send_message(message.chat.id, "Ласкаво просимо, Адміністраторе!", reply_markup=markup)
    else:
        if not is_registered(message.chat.id):  # Перевіряємо, чи користувач новий
            welcome_new_user(message)
        else:
            bot.send_message(message.chat.id,
                             "Даний бот створений для контролю стану здоров`я мешканців гуртожитку.\n\nДоступні команди:\n\n/poll - пройти опитування\n/rename - змінити прізвище/номер кімнати\n/mytemp - статистика температури")
@bot.message_handler(commands=['poll'])
def poll(message):
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    people_id = message.chat.id
    cursor.execute("SELECT id FROM login_id WHERE id = ?", (people_id,))
    data = cursor.fetchone()
    if data is None:
        user_id = message.chat.id
        user_name = message.from_user.first_name
        user_room = None
        cursor.execute("INSERT INTO login_id VALUES (?, ?, ?);", (user_id, user_name, user_room))
        connect.commit()
    u = message.from_user.username
    markup = types.InlineKeyboardMarkup(row_width=2)
    item = types.InlineKeyboardButton('Ні', callback_data='question_1')
    item2 = types.InlineKeyboardButton('Так', callback_data='question_2')
    markup.add(item, item2)
    bot.send_message(message.chat.id, 'Чи присутній кашель?', reply_markup=markup)
    connect.close()

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    people_id = call.message.chat.id
    u = call.message.chat.username

    if call.data == 'question_1':
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id, text='Кашель відсутній')
        markup = types.InlineKeyboardMarkup(row_width=2)
        item5 = types.InlineKeyboardButton('Ні', callback_data='question_5')
        item6 = types.InlineKeyboardButton('Так', callback_data='question_6')
        markup.add(item5, item6)
        bot.send_message(call.message.chat.id, 'Чи відчуваються запахи/смаки?', reply_markup=markup)

    elif call.data == 'regist':
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id,
                              text='Введіть наступні значення:')
        bot.send_message(call.message.chat.id, "Вкажіть своє прізвище")
        bot.register_next_step_handler(call.message, name_func)

    elif call.data == 'question_2':
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id, text='Кашель наявний')
        markup = types.InlineKeyboardMarkup(row_width=2)
        item3 = types.InlineKeyboardButton('Ні', callback_data='question_3')
        item4 = types.InlineKeyboardButton('Так', callback_data='question_4')
        markup.add(item3, item4)
        bot.send_message(call.message.chat.id, 'Чи відчуваються запахи/смаки?', reply_markup=markup)

    elif call.data == 'question_4':
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id,
                              text='Запахи та смаки відчуваються')
        cursor.execute(f"SELECT name FROM login_id WHERE id = {people_id}")
        rows = cursor.fetchone()
        cursor.execute(f"SELECT room FROM login_id WHERE id = {people_id}")
        ro = cursor.fetchone()
        for r in ro:
            for row in rows:
                bot.send_message('ADMIN_ID', f"Присутній кашель у {row} кімната {r}. Користувач @{u}")
        bot.send_message(call.message.chat.id, "Вкажіть свою температуру\n_Приклад: 36\.6, 37_",
                         parse_mode='MarkdownV2')
        bot.register_next_step_handler(call.message, tempa)

    elif call.data == 'question_3':
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id,
                              text='Запахи та смаки не відчуваються')
        cursor.execute(f"SELECT name FROM login_id WHERE id = {people_id}")
        rows = cursor.fetchone()
        cursor.execute(f"SELECT room FROM login_id WHERE id = {people_id}")
        ro = cursor.fetchone()
        for r in ro:
            for row in rows:
                bot.send_message('ADMIN_ID',
                                 f"Присутній кашель, запахи та смаки не відчуваються у {row} кімната {r}. Користувач @{u}")
        bot.send_message(call.message.chat.id, "Вкажіть свою температуру\n_Приклад: 36\.6, 37_",
                         parse_mode='MarkdownV2')
        bot.register_next_step_handler(call.message, tempa)

    elif call.data == 'question_5':
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id,
                              text='Запахи та смаки не відчуваються')
        cursor.execute(f"SELECT name FROM login_id WHERE id = {people_id}")
        rows = cursor.fetchone()
        cursor.execute(f"SELECT room FROM login_id WHERE id = {people_id}")
        ro = cursor.fetchone()
        for r in ro:
            for row in rows:
                bot.send_message('ADMIN_ID', f"Запахи та смаки не відчуваються у {row} кімната {r}. Користувач @{u}")
        bot.send_message(call.message.chat.id, "Вкажіть свою температуру\n_Приклад: 36\.6, 37_",
                         parse_mode='MarkdownV2')
        bot.register_next_step_handler(call.message, tempa)

    elif call.data == 'question_6':
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id,
                              text='Запахи та смаки відчуваються')
        bot.send_message(call.message.chat.id, "Вкажіть свою температуру\n_Приклад: 36\.6, 37_",
                         parse_mode='MarkdownV2')
        bot.register_next_step_handler(call.message, tempa)

    connect.close()

@bot.message_handler(commands=['rename'])
def name(message):
    bot.send_message(message.chat.id, "Вкажіть своє прізвище")
    bot.register_next_step_handler(message, name_func)

def name_func(message):
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    message_name = message.text
    people_id = message.chat.id
    cursor.execute("UPDATE login_id SET name = ? WHERE id = ?", (message_name, people_id))
    connect.commit()
    bot.send_message(message.chat.id, "Вкажіть номер своєї кімнати")
    bot.register_next_step_handler(message, room_func)
    connect.close()

def room_func(message):
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    message_room = message.text
    people_id = message.chat.id

    if message_room.strip() != "":
        cursor.execute("UPDATE login_id SET room = ? WHERE id = ?", (message_room, people_id))
        connect.commit()
        bot.send_message(message.chat.id, "Дані збережені")
        bot.send_message(message.chat.id,
                         "Даний бот створений для контролю стану здоров`я мешканців гуртожитку.\n\nДоступні команди:\n\n/poll - пройти опитування\n/rename - змінити прізвище/номер кімнати\n/mytemp - статистика температури")

    else:
        bot.send_message(message.chat.id, "Номер кімнати не може бути порожнім. Спробуйте ще раз.")
        bot.register_next_step_handler(message, room_func)

    connect.close()

def is_number(message):
    arr = message.text.split(".")
    if len(message.text) == 0 or len(arr) > 2:
        return False
    for i in arr:
        if not i.isnumeric():
            return False
    return True

def tempa(message):
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    message_temp = message.text
    people_id = message.chat.id
    user_time = datetime.fromtimestamp(time.time())
    ust = str(user_time)
    ut = ust[:19]
    cursor.execute("SELECT name FROM login_id WHERE id = ?", (people_id,))
    name_row = cursor.fetchone()
    if name_row:
        name = name_row[0]
    else:
        name = message.from_user.first_name
    login = message.from_user.username
    if is_number(message):
        cursor.execute(
            "INSERT INTO temp_id (name, date, temp) VALUES (?, ?, ?);",
            (name, ut, message_temp))

        connect.commit()
        temperaturka = float(message_temp)
        if temperaturka >= 37.2:
            cursor.execute(f"SELECT name FROM login_id WHERE id = {people_id}")
            rows = cursor.fetchone()
            cursor.execute(f"SELECT room FROM login_id WHERE id = {people_id}")
            ro = cursor.fetchone()
            for r in ro:
                for row in rows:
                    bot.send_message('ADMIN_ID', f"Підвищена температура у {row} кімната {r}. Користувач @{login}")
        bot.send_message(people_id, "Дані збережено. Дякуємо за пройденне опитування!")
        bot.send_message(message.chat.id,"Даний бот створений для контролю стану здоров`я мешканців гуртожитку.\n\nДоступні команди:\n\n/poll - пройти опитування\n/rename - змінити прізвище/номер кімнати\n/mytemp - статистика температури")
    else:
        bot.send_message(people_id, "Спробуйте ввести коректне значення")
        bot.register_next_step_handler(message, tempa)
    connect.close()

@bot.message_handler(func=lambda message: message.text == "Розіслати повідомлення")
def handle_broadcast_button(message):
    if message.chat.id == ADMIN_ID:
        bot.send_message(message.chat.id, "Введіть повідомлення для розсилки:")
        bot.register_next_step_handler(message, send_broadcast)
    else:
        bot.send_message(message.chat.id, "У вас немає прав для використання цієї команди.")

@bot.message_handler(func=lambda message: message.text == "Примусове опитування")
def handle_force_poll_button(message):
    if message.chat.id == ADMIN_ID:
        force_poll(message)
    else:
        bot.send_message(message.chat.id, "У вас немає прав для використання цієї команди.")
def force_poll(message):
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    cursor.execute("SELECT id FROM login_id")
    rows = cursor.fetchall()
    blocked_users = []  # Створюємо список для зберігання ID користувачів, які заблокували бота
    for row in rows:
        user_id = row[0]
        if user_id != ADMIN_ID:  # Перевіряємо, чи не є це ID адміністратора
            try:
                bot.send_message(user_id, "Нагадування про щоденне опитування\nПройти /poll")
                print(f"Повідомлення про опитування надіслано користувачу з ID: {user_id}")
            except telebot.apihelper.ApiTelegramException as e:
                if e.result_json['description'] == "Forbidden: bot was blocked by the user":
                    blocked_users.append(user_id)
                    bot.send_message(ADMIN_ID, "Повідомлення про опитування було надіслано.")
    connect.close()

    if blocked_users:
        print(f"Бот був заблокований користувачами з ID: {blocked_users}")
    else:
        bot.send_message(message.chat.id, "Повідомлення про опитування було надіслано всім користувачам, крім адміністратора.")
        print("Повідомлення про опитування було надіслано всім користувачам, крім адміністратора.")


def send_broadcast(message):
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    cursor.execute("SELECT id FROM login_id")
    rows = cursor.fetchall()
    blocked_users = []  # Створюємо список для зберігання ID користувачів, які заблокували бота
    for row in rows:
        user_id = row[0]
        if user_id != ADMIN_ID:  # Перевіряємо, чи не є це ID адміністратора
            try:
                bot.send_message(user_id, message.text)
                print(f"Повідомлення надіслано користувачу з ID: {user_id}")
            except telebot.apihelper.ApiTelegramException as e:
                if e.result_json['description'] == "Forbidden: bot was blocked by the user":
                    blocked_users.append(user_id)
    connect.close()

    if blocked_users:
        print(f"Бот був заблокований користувачами з ID: {blocked_users}")

    if message.chat.id == ADMIN_ID:
        bot.send_message(message.chat.id, "Повідомлення було надіслано всім користувачам.")
        print("Повідомлення було надіслано всім користувачам, крім адміністратора.")

@bot.message_handler(commands=['mytemp'])
def my_temp(message):
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    user_id = message.chat.id
    cursor.execute("SELECT name FROM login_id WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        user_name = row[0]  # Отримуємо ім'я користувача
        cursor.execute("SELECT * FROM temp_id WHERE name = ?", (user_name,))
        rows = cursor.fetchall()
        if rows:
            response = "Статистика вашої температури:\n"
            for row in rows:
                response += f"Дата: {row[1]}, Температура: {row[2]}\n"
            bot.send_message(message.chat.id, response)
        else:
            bot.send_message(message.chat.id, "На жаль, в базі даних немає записів про вашу температуру.")
    else:
        bot.send_message(message.chat.id, "Ви не авторизовані. Будь ласка, спочатку пройдіть реєстрацію. /start")
    connect.close()


if __name__ == '__main__':
    bot.polling(none_stop=True, interval=0)
