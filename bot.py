import telebot
from telebot import types
import os
import PyPDF2
from fpdf import FPDF
from dotenv import load_dotenv

# Хондани маълумот аз файли .env
load_dotenv()

TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    raise ValueError("Токен ёфт нашуд! Лутфан файли .env-ро санҷед ва BOT_TOKEN-ро илова кунед.")

bot = telebot.TeleBot(TOKEN)
users_data = {}

FONTS_DIR = r'C:\Users\HASANBOY\Desktop\БОТ\fonts'
TEMP_DIR = 'temp/'

if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def get_available_fonts():
    fonts_dict = {}
    if os.path.exists(FONTS_DIR):
        for file in os.listdir(FONTS_DIR):
            if file.lower().endswith('.ttf'):
                font_name = os.path.splitext(file)[0]
                fonts_dict[font_name] = file
    return fonts_dict

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton('Навиштаҷот'), types.KeyboardButton('PDF'))
    return markup

def fonts_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    available_fonts = get_available_fonts()
    if not available_fonts:
        markup.add(types.KeyboardButton("Шрифт ёфт нашуд"))
        return markup
    buttons = [types.KeyboardButton(name) for name in available_fonts.keys()]
    markup.add(*buttons)
    return markup

# Клавиатура барои интихоби андозаи шрифт
def sizes_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)
    sizes = ['10', '12', '14', '16', '18', '20', '24', '28', '32', '36', '48', '72']
    buttons = [types.KeyboardButton(s) for s in sizes]
    markup.add(*buttons)
    return markup

def post_generation_keyboard():
    markup = types.InlineKeyboardMarkup()
    btn_data = types.InlineKeyboardButton('Ивази маълумот', callback_data='change_data')
    btn_font = types.InlineKeyboardButton('Ивази шрифт', callback_data='change_font')
    markup.add(btn_data, btn_font)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, 
                     "Салом! Интихоб кунед, ки чӣ фиристодан мехоҳед:\n\n"
                     "📝 **Навиштаҷот** - Матн мефиристед ва ман онро ба PDF табдил медиҳам.\n"
                     "📄 **PDF** - Файли PDF мефиристед ва ман матни онро бо шрифти нав месозам.", 
                     reply_markup=main_keyboard(), parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == 'Навиштаҷот')
def handle_text_button(message):
    users_data[message.chat.id] = {'type': 'text'}
    msg = bot.send_message(message.chat.id, "Лутфан, матни худро равон кунед:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_text_input)

def process_text_input(message):
    if not message.text:
        msg = bot.send_message(message.chat.id, "Лутфан, танҳо матн равон кунед!")
        bot.register_next_step_handler(msg, process_text_input)
        return
    
    users_data[message.chat.id]['content'] = message.text
    msg = bot.send_message(message.chat.id, "Акнун шрифтро интихоб кунед:", reply_markup=fonts_keyboard())
    # Ба ҷои generate_pdf аввал шрифтро қабул мекунем
    bot.register_next_step_handler(msg, process_font_selection)

@bot.message_handler(func=lambda message: message.text == 'PDF')
def handle_pdf_button(message):
    users_data[message.chat.id] = {'type': 'pdf'}
    msg = bot.send_message(message.chat.id, "Лутфан, файли PDF-ро равон кунед:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_pdf_input)

def process_pdf_input(message):
    if not message.document or not message.document.file_name.endswith('.pdf'):
        msg = bot.send_message(message.chat.id, "Лутфан, маҳз файли формати PDF равон кунед!")
        bot.register_next_step_handler(msg, process_pdf_input)
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        pdf_path = os.path.join(TEMP_DIR, f"{message.chat.id}_input.pdf")
        with open(pdf_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        text = ""
        with open(pdf_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        
        os.remove(pdf_path)
        
        if not text.strip():
            bot.send_message(message.chat.id, "Мутаассифона, аз ин PDF ягон матн хонда натавонистам (шояд он расм бошад).", reply_markup=main_keyboard())
            return
            
        users_data[message.chat.id]['content'] = text
        msg = bot.send_message(message.chat.id, "Файл қабул шуд! Акнун шрифтро интихоб кунед:", reply_markup=fonts_keyboard())
        bot.register_next_step_handler(msg, process_font_selection)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"Хатогӣ ҳангоми қабули файл: {e}", reply_markup=main_keyboard())

# Қадами 1: Қабули шрифт ва пурсидани андозаи он
def process_font_selection(message):
    font_choice = message.text
    chat_id = message.chat.id
    available_fonts = get_available_fonts()
    
    if font_choice not in available_fonts:
        msg = bot.send_message(chat_id, "Лутфан, шрифтро маҳз аз тугмаҳои поён интихоб кунед!", reply_markup=fonts_keyboard())
        bot.register_next_step_handler(msg, process_font_selection)
        return
        
    users_data[chat_id]['font'] = font_choice
    msg = bot.send_message(chat_id, "Андозаи шрифтро интихоб кунед (ё худатон рақамашро нависед):", reply_markup=sizes_keyboard())
    bot.register_next_step_handler(msg, generate_pdf)

# Қадами 2: Қабули андоза ва сохтани PDF
def generate_pdf(message):
    chat_id = message.chat.id
    size_text = message.text
    
    # Санҷиш: оё андозаи фиристодашуда рақам аст
    if not size_text.isdigit() or not (8 <= int(size_text) <= 150):
        msg = bot.send_message(chat_id, "Лутфан, андозаро ҳамчун рақам нависед (масалан: 14):", reply_markup=sizes_keyboard())
        bot.register_next_step_handler(msg, generate_pdf)
        return
        
    font_size = int(size_text)
    
    # Фиристодани паёми интизорӣ ва нигоҳ доштани он
    wait_msg = bot.send_message(chat_id, "⏳ Файли шумо омода шуда истодааст, лутфан интизор шавед...", reply_markup=types.ReplyKeyboardRemove())
    
    try:
        content_text = users_data.get(chat_id, {}).get('content', '')
        font_choice = users_data.get(chat_id, {}).get('font', '')
        
        if not content_text or not font_choice:
            bot.send_message(chat_id, "Хатогӣ: Маълумот ёфт нашуд. Лутфан аз нав оғоз кунед.", reply_markup=main_keyboard())
            return

        available_fonts = get_available_fonts()
        font_filename = available_fonts[font_choice]
        font_path = os.path.join(FONTS_DIR, font_filename)
        
        pdf = FPDF()
        pdf.add_page()
        
        pdf.add_font(font_choice, '', font_path, uni=True)
        # Истифодаи андозаи интихобкардаи истифодабаранда
        pdf.set_font(font_choice, '', font_size)
        pdf.set_text_color(0, 0, 255)
        pdf.multi_cell(0, int(font_size * 0.4) + 4, content_text) # Фосилаи сатрҳоро мувофиқи андоза танзим мекунем
        
        output_pdf_path = os.path.join(TEMP_DIR, f"Result_{chat_id}.pdf")
        pdf.output(output_pdf_path)
        
        with open(output_pdf_path, 'rb') as doc:
            bot.send_document(chat_id, doc, caption="Файли шумо омода аст! 💙\n\nМехоҳед ягон амали дигарро иҷро кунед?", reply_markup=post_generation_keyboard())
            
        os.remove(output_pdf_path)
        
        # Нест кардани паёми "⏳ Файли шумо омода шуда истодааст..."
        try:
            bot.delete_message(chat_id, wait_msg.message_id)
        except:
            pass # Агар истифодабаранда паёмро пешакӣ нест карда бошад, хатогӣ намедиҳад
            
    except Exception as e:
        # Дар ҳолати хатогӣ ҳам паёми интизорӣ нест карда мешавад
        try:
            bot.delete_message(chat_id, wait_msg.message_id)
        except:
            pass
        bot.send_message(chat_id, f"Хатогӣ ҳангоми сохтани PDF: {e}", reply_markup=main_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    chat_id = call.message.chat.id
    
    if call.data == 'change_data':
        bot.send_message(chat_id, "Лутфан интихоб кунед, ки кадом намуди маълумотро фиристодан мехоҳед:", reply_markup=main_keyboard())
        
    elif call.data == 'change_font':
        if chat_id in users_data and 'content' in users_data[chat_id]:
            msg = bot.send_message(chat_id, "Хеле хуб! Матни шумо дар хотир аст. Лутфан, шрифти навро интихоб кунед:", reply_markup=fonts_keyboard())
            # Акнун боз ба қадами интихоби шрифт бармегардем
            bot.register_next_step_handler(msg, process_font_selection)
        else:
            bot.send_message(chat_id, "Мутаассифона, матни пештара ёфт нашуд. Лутфан, аз нав оғоз кунед.", reply_markup=main_keyboard())
            
    bot.answer_callback_query(call.id)

if __name__ == '__main__':
    print("Бот бо муваффақият ба кор даромад...")
    bot.infinity_polling()