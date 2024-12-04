import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
import random
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize bot with your token
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

# Temporary storage for user sessions
user_sessions = {}

class UserSession:
    def __init__(self, initial_url):
        self.current_url = initial_url
        self.current_paragraph_index = 0
        self.paragraphs = []

# Function to initialize Selenium WebDriver
def init_driver():
    browser_options = Options()
    browser_options.add_argument('--headless')
    browser_options.add_argument('--disable-gpu')
    browser_options.add_argument('--no-sandbox')
    driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=browser_options)
    return driver

# Function to scrape Wikipedia content using Selenium
def get_wikipedia_content(query):
    driver = init_driver()
    try:
        url = f"https://ru.wikipedia.org/wiki/{query.replace(' ', '_')}"
        driver.get(url)
        paragraphs = driver.find_elements(By.TAG_NAME, "p")
        content = [p.text for p in paragraphs if p.text.strip() != '']
        driver.quit()
        return url, content
    except Exception as e:
        driver.quit()
        return None, [f"Error retrieving content: {str(e)}"]

# Function to get related articles from Wikipedia page
def get_related_articles(driver):
    related_links = []
    for element in driver.find_elements(By.TAG_NAME, 'div'):
        if element.get_attribute('class') == 'hatnote navigation-not-searchable':
            links = element.find_elements(By.TAG_NAME, 'a')
            for link in links:
                title = link.get_attribute('title')
                related_links.append(title)
    return related_links

# Start command
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Добро пожаловать в Википедийный бот! Напишите ваш запрос для начала работы. Далее вы можете двигаться по параграфам найденной статьи, открывать случайную вложенную статью или написать новый запрос.")

# Handle queries
@bot.message_handler(func=lambda message: True)
def handle_query(message):
    query = message.text
    chat_id = message.chat.id
    try:
        url, paragraphs = get_wikipedia_content(query)
        if paragraphs:
            user_sessions[chat_id] = UserSession(url)
            user_sessions[chat_id].paragraphs = paragraphs
            send_article_content(chat_id, 0)
        else:
            bot.send_message(chat_id, "Ничего не найдено по вашему запросу.")
    except Exception as e:
        bot.send_message(chat_id, f"Error: {str(e)}")

# Function to display article content
def send_article_content(chat_id, paragraph_index):
    session = user_sessions.get(chat_id)
    if not session or paragraph_index < 0 or paragraph_index >= len(session.paragraphs):
        bot.send_message(chat_id, "Нет доступных параграфов.")
        return

    session.current_paragraph_index = paragraph_index
    paragraph = session.paragraphs[paragraph_index]

    keyboard = InlineKeyboardMarkup(row_width=3)
    prev_button = InlineKeyboardButton("<<<", callback_data='prev', disabled=(paragraph_index == 0))
    next_button = InlineKeyboardButton(">>>", callback_data='next', disabled=(paragraph_index == len(session.paragraphs) - 1))
    relt_button = InlineKeyboardButton("..статья..", callback_data='related')
    keyboard.add(prev_button, relt_button, next_button)

    bot.send_message(chat_id, paragraph, reply_markup=keyboard)

# Handle button callbacks
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    session = user_sessions.get(chat_id)

    if not session:
        bot.answer_callback_query(call.id, "Сессия истекла. Пожалуйста, введите новый запрос.")
        return

    if call.data == 'next':
        send_article_content(chat_id, session.current_paragraph_index + 1)
    elif call.data == 'prev':
        send_article_content(chat_id, session.current_paragraph_index - 1)
    elif call.data == 'related':
        driver = init_driver()
        try:
            driver.get(session.current_url)
            related_articles = get_related_articles(driver)
            driver.quit()
            if related_articles:
                random_article = random.choice(related_articles)
                print(random_article)
                url, paragraphs = get_wikipedia_content(random_article)
                if paragraphs:
                    session.current_url = url
                    session.paragraphs = paragraphs
                    send_article_content(chat_id, 0)
                else:
                    bot.send_message(chat_id, "Не удалось загрузить связанную статью.")
            else:
                bot.send_message(chat_id, "Нет доступных связанных статей.")
        except Exception as e:
            driver.quit()
            bot.send_message(chat_id, f"Error: {str(e)}")

if __name__ == '__main__':
    bot.polling(none_stop=True)
