# Before running (pip install beautifulsoup4,lxml,python-telegram-bot,pandas)
import csv
import json
import os
import shutil
import sqlite3

import pandas as pd
import requests
import telegram
from bs4 import BeautifulSoup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters


# !!!before using create a folder \Products\!!!if you don't do it -- press start twice.
def start_new_proc():
    """ this function checks do we have a folder and all files from other session. If we have got some files ,
    function del it and create new,else create new files and folder """
    folder = "Products"
    if not os.path.exists(folder):
        os.mkdir(folder)
    else:
        shutil.rmtree(folder, ignore_errors=False)
        for File in ["table_all_products.db", "code.html", "category.json"]:
            if os.path.exists(File):
                os.remove(File)


start_new_proc()

print("Start process")
# Input link from browser
url = 'https://health-diet.ru/table_calorie/'
# Input "accept and User-Agent" for headers from Developer Console.
headers = {
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/100.0.4896.127 Safari/537.36"

}
# We add a path to the headers so that the site perceives us as a user, not a bot.
req = requests.get(url, headers=headers)

list_code = req.text

# Create and save all code information in html file.
with open("code.html", "w") as file:
    file.write(list_code)

# # write all information on generated file

# open code.html and find products category class.
with open("code.html") as file:
    list_code = file.read()
soup = BeautifulSoup(list_code, "lxml")

prod_groups = soup.find_all(class_="mzr-tc-group-item-href")

# Create new dict, named  - category.
category = {}
for i in prod_groups:
    i_name = i.text
    i_href = "https://health-diet.ru" + i.get("href")
    category[i_name] = i_href

#  Create file "category.json" and save all categories and links about.
with open("category.json", "w") as file:
    json.dump(category, file, indent=4, ensure_ascii=False)
# create variable " count " - because we need to take only first 38 position from catalog.
count = 1

# Then we create for all categories html files and enumerate it.

with open("category.json") as file_1:
    category = json.load(file_1)
    for k, v in category.items():
        link = requests.get(url=v, headers=headers)
        list_code = link.text
        with open(f"Products/{count}_{k}.html", "w", encoding="utf-8") as file:
            file.write(list_code)
        with open(f"Products/{count}_{k}.html", encoding="utf-8") as file:
            list_code = file.read()

        # Then we search for all products from all categories.

        soup = BeautifulSoup(list_code, "lxml")

        head = soup.find(class_="mzr-tc-group-table").find("tr").find_all("th")

        products = head[0].text
        KKal = head[1].text
        # Create csv files for all categories number/category
        with open(f'Products/{count}_{k}.csv', "w", encoding="utf-8") as file_2:

            writer = csv.writer(file_2)
            writer.writerow((products,
                             KKal))

        products_name = soup.find(class_="mzr-tc-group-table").find("tbody").find_all("tr")
        # create dict all_info , update it all products and KKal/100 gram
        all_info = {}

        for i in products_name:
            products_td = i.find_all("td")

            title = products_td[0].find("a").text
            KKal = products_td[1].text

            all_info.update({
                title: KKal

            })
            # write information to our csv file
            with open(f'Products/{count}_{k}.csv', "a", encoding="utf-8") as file_2:
                writer = csv.writer(file_2)
                writer.writerow((title,
                                 KKal))
        # write information to our json file
        with open(f'Products/{k}.json', "a", encoding="utf-8") as file:
            json.dump(all_info, file, indent=4, ensure_ascii=False)

        count += 1
        if count == 39:
            break
        print(39 - count, k)
    print("Process completed", "\nData collected")

# create new dict only(num\category)for use in TelegramBot
num = [i for i in range(1, 39)]
category_name = []

with open("category.json") as file_1:
    category = json.load(file_1)
    for k, v in category.items():
        category_name.append(k)
num_category = dict(zip(num, category_name))
# Create new database file and connection
with sqlite3.connect("table_all_products.db") as conn:
    c = conn.cursor()
    # create a table with three columns and call it.
    c.execute('create table if not exists category_base (Category,Products,Description )')
    conn.commit()
    # find all information for our table and fill in our columns
    for k, v in num_category.items():

        with open(f"Products/{v}.json", "r", encoding='utf-8') as file:
            res = json.load(file)
            for pos, prod in res.items():
                c.executemany('insert into category_base VALUES (?, ?, ?)',
                              [(f'{k}', f'{pos}', f'{prod}')
                               ])
    conn.commit()
    # for comfort reading print it with pandas module
    print(pd.read_sql_query("SELECT * FROM category_base", conn))
# Run our telegram bot
print("The bot is running. Press Ctrl+C to finish")


def on_start(update, context):
    """ this function create start message for User """
    chat = update.effective_chat
    context.bot.send_message(chat_id=chat.id,
                             text=f"Hello, which product do you want to know the calorie content?"
                                  f"\n\n{num_category}\n\n\nPress num of category :")


def on_message(update, context):
    """ this function checks User message int or not , if answer is integer ,
    bot write all info from selected category ,else return "What are you interested in - press number of Category?
    User can try again. """
    chat = update.effective_chat
    text = update.message.text
    try:

        prod_call = int(text)
        for n, t in num_category.items():
            if n == prod_call:
                with open(f"Products/{t}.json", "r", encoding='utf-8') as file:
                    result = json.load(file)

                    for g, j in result.items():
                        answer = f'{g} : {j} in 100 gram'
                        context.bot.send_message(chat_id=chat.id, text=answer)



    except:
        context.bot.send_message(chat_id=chat.id, text=f"What are you interested in - press number of Category?\n\n"
                                                       f"{num_category}\n\n try again check number : ")


# create bot with BotFather , add your token.

TOKEN = "5331416441:AAHReoROpXol-tbmdTjV_EpjtZuwgmklr-4"
bot = telegram.Bot(token=TOKEN)

updater = Updater(TOKEN, use_context=True)

dispatcher = updater.dispatcher
dispatcher.add_handler(CommandHandler("start", on_start))
dispatcher.add_handler(MessageHandler(Filters.all, on_message))

updater.start_polling()
updater.idle()
