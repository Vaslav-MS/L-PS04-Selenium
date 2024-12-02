import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager

#browser = webdriver.Firefox()
#browser.get('https://ru.wikipedia.org/wiki/%D0%A1%D0%BE%D0%BB%D0%BD%D0%B5%D1%87%D0%BD%D0%B0%D1%8F_%D1%81%D0%B8%D1%81%D1%82%D0%B5%D0%BC%D0%B0')
#statnotes = []
#for element in browser.find_elements(By.TAG_NAME, 'div'):
#    if element.get_attribute('class') == 'hatnote navigation-not-searchable':
#        statnotes.append(element)
#for statnote in statnotes:
#    link = statnote.find_element(By.TAG_NAME, 'a').get_attribute('href')
#    link = statnote.find_element(By.TAG_NAME, 'a').get_attribute('title')
#    print(link)

# Initialize bot with your token
BOT_TOKEN = '7823676791:AAFsMtrS6NhFuMVkYDrsnNyuOmFZsBQe6Os'
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
        url = f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}"
        driver.get(url)
        paragraphs = driver.find_elements(By.CSS_SELECTOR, "p")
        content = [p.text for p in paragraphs if p.text.strip() != '']
        driver.quit()
        return url, content
    except Exception as e:
        driver.quit()
        return None, [f"Error retrieving content: {str(e)}"]

# Start command
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Добро пожаловать в Википедийный бот! Отправьте мне ваш запрос для начала работы.")

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
        bot.send_message(chat_id, "Нет больше доступных параграфов.")
        return

    session.current_paragraph_index = paragraph_index
    paragraph = session.paragraphs[paragraph_index]

    keyboard = InlineKeyboardMarkup()
    if paragraph_index > 0:
        keyboard.add(InlineKeyboardButton("Предыдущий", callback_data='prev'))
    if paragraph_index < len(session.paragraphs) - 1:
        keyboard.add(InlineKeyboardButton("Следующий", callback_data='next'))
    keyboard.add(InlineKeyboardButton("Похожие статьи", callback_data='related'))

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
        bot.send_message(chat_id, "Функция просмотра связанных статей находится в разработке.")

if __name__ == '__main__':
    bot.polling(none_stop=True)
