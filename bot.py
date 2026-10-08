import os
import json
import textwrap
import random
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image, ImageDraw, ImageFont
from fpdf import FPDF
import PyPDF2
import docx
from dotenv import load_dotenv
import time

# ==========================================
# 1. ТАНЗИМОТИ АСОСӢ ВА РОҲҲО
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
FONTS_FILE = os.path.join(BASE_DIR, "fonts.json")
ADMINS_FILE = os.path.join(BASE_DIR, "admins.json")
CHANNELS_FILE = os.path.join(BASE_DIR, "channels.json")

for folder in [FONTS_DIR, TEMP_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

load_dotenv(os.path.join(BASE_DIR, ".env"))
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0)) 
bot = telebot.TeleBot(BOT_TOKEN)

user_data = {}

COLORS = {
    'blue': {'name': '🔵 Кабуд', 'rgb': (15, 20, 120)},
    'black': {'name': '⚫️ Сиёҳ', 'rgb': (20, 20, 20)},
    'red': {'name': '🔴 Сурх', 'rgb': (150, 20, 20)},
    'green': {'name': '🟢 Сабз', 'rgb': (15, 110, 30)},
    'purple': {'name': '🟣 Бунафш', 'rgb': (100, 20, 150)}
}

PAPERS = {
    'plain': '⬜️ Оддӣ',
    'lined': '📝 Хатакдор',
    'squared': '▦ Катакдор'
}

# МАТНИ ТУГМАҲО
BTN_FONT = "🔤 Шрифт"
BTN_COLOR = "🎨 Ранг"
BTN_PAPER = "📔 Варақа"
BTN_FORMAT = "💾 Формат (PDF/Расм)"
BTN_GENERATE = "✅ ТАВЛИД КАРДАН"
BTN_BACK = "🔙 Бозгашт"
BTN_ADMIN_BACK = "🔙 Менюи Админ"
BTN_MAIN_BACK = "🔙 Бозгашт (Асосӣ)"

# ==========================================
# 2. МЕНЕҶЕРИ ФАЙЛҲО
# ==========================================
def load_json(file_path, default_data):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, ensure_ascii=False, indent=4)
        return default_data

def save_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

FONTS = load_json(FONTS_FILE, {})
SUB_ADMINS = load_json(ADMINS_FILE, [])
CHANNELS = load_json(CHANNELS_FILE, {}) 

# ==========================================
# 3. СИСТЕМАИ ОБУНАИ МАҶБУРӢ
# ==========================================
def get_unsubscribed_channels(user_id):
    unsubbed = {}
    for ch_id, link in CHANNELS.items():
        try:
            member = bot.get_chat_member(ch_id, user_id)
            if member.status in ['left', 'kicked']:
                unsubbed[ch_id] = link
        except Exception:
            pass 
    return unsubbed

def enforce_subscription(chat_id):
    if chat_id == ADMIN_ID or chat_id in SUB_ADMINS:
        return True 
    
    unsubbed = get_unsubscribed_channels(chat_id)
    if unsubbed:
        markup = InlineKeyboardMarkup()
        for ch_id, link in unsubbed.items():
            markup.add(InlineKeyboardButton("📢 Обуна шудан", url=link))
        markup.add(InlineKeyboardButton("✅ Тафтиш кардан", callback_data="check_sub"))
        
        bot.send_message(
            chat_id, 
            "⚠️ **Барои истифодаи бот, лутфан ба каналҳои зерин обуна шавед:**", 
            parse_mode="Markdown", 
            reply_markup=markup
        )
        return False
    return True

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def handle_check_sub(call):
    chat_id = call.message.chat.id
    unsubbed = get_unsubscribed_channels(chat_id)
    if unsubbed:
        bot.answer_callback_query(call.id, "❌ Шумо то ҳол ба ҳамаи каналҳо обуна нашудаед!", show_alert=True)
    else:
        bot.answer_callback_query(call.id, "✅ Обуна тасдиқ шуд! Хуш омадед.", show_alert=True)
        bot.delete_message(chat_id, call.message.message_id)
        if chat_id in user_data and user_data[chat_id].get('content'):
            send_dashboard(chat_id)
        else:
            bot.send_message(chat_id, "👇 *Лутфан акнун матн ё файли худро равон кунед:*", parse_mode="Markdown")

# ==========================================
# 4. ФУНКСИЯҲОИ КОРБАР ВА ГЕНЕРАТСИЯ
# ==========================================
def init_user(chat_id):
    first_font_name = list(FONTS.keys())[0] if FONTS else "Default"
    first_font_file = FONTS.get(first_font_name, "")
    if chat_id not in user_data:
        user_data[chat_id] = {
            'font_name': first_font_name,
            'font_file': first_font_file,
            'color': 'blue', 'paper': 'lined', 'format': 'pdf', 
            'content': None, 'admin_state': None, 'user_state': None, 'temp_data': None
        }
    else:
        if user_data[chat_id]['font_name'] not in FONTS and FONTS:
            user_data[chat_id]['font_name'] = first_font_name
            user_data[chat_id]['font_file'] = first_font_file
    return user_data[chat_id]

def send_dashboard(chat_id, custom_text=None):
    ud = init_user(chat_id)
    if not ud.get('content'):
        bot.send_message(chat_id, "👇 *Лутфан аввал матн ё файли худро равон кунед, сипас меню пайдо мешавад:*", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
        return

    font_display = ud['font_name'] if FONTS else "Шрифт нест ❌"
    format_display = "PDF 📄" if ud.get('format', 'pdf') == 'pdf' else "Расмҳо 🖼"
    
    text = custom_text if custom_text else (
        "⚙️ **Танзимоти Дастнависи шумо:**\n\n"
        f"🔤 **Шрифт:** {font_display}\n"
        f"🎨 **Ранг:** {COLORS[ud['color']]['name']}\n"
        f"📔 **Варақа:** {PAPERS[ud['paper']]}\n"
        f"💾 **Формат:** {format_display}\n\n"
        "👇 *Агар омода бошед, 'ТАВЛИД КАРДАН'-ро пахш намоед:*"
    )
    
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton(BTN_FONT), KeyboardButton(BTN_COLOR))
    markup.add(KeyboardButton(BTN_PAPER), KeyboardButton(BTN_FORMAT))
    markup.add(KeyboardButton(BTN_GENERATE))
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

def create_new_page(paper_type, img_width, img_height, font_size, line_spacing):
    image = Image.new('RGB', (img_width, img_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    if paper_type == 'lined':
        draw.line([(100, 0), (100, img_height)], fill=(255, 100, 100), width=2)
        for y in range(120 + font_size, img_height, line_spacing):
            draw.line([(0, y), (img_width, y)], fill=(200, 220, 255), width=2)
    elif paper_type == 'squared':
        grid_size = 40
        draw.line([(100, 0), (100, img_height)], fill=(255, 100, 100), width=2)
        for y in range(0, img_height, grid_size):
            draw.line([(0, y), (img_width, y)], fill=(210, 230, 255), width=1)
        for x in range(0, img_width, grid_size):
            draw.line([(x, 0), (x, img_height)], fill=(210, 230, 255), width=1)
    return image, draw

def generate_handwritten_images(chat_id, progress_callback=None):
    ud = user_data[chat_id]
    text = ud['content']
    font_path = os.path.join(FONTS_DIR, ud['font_file'])
    font_size, line_spacing = 40, 55 
    img_width, img_height = 1240, 1754 
    left_margin, right_margin = 130, 80
    max_text_width = img_width - left_margin - right_margin
    bottom_margin = 150 
    max_y = img_height - bottom_margin
    
    try: font = ImageFont.truetype(font_path, font_size)
    except: font = ImageFont.load_default()

    dummy_img = Image.new('RGB', (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    
    lines = []
    for paragraph in text.split('\n'):
        if not paragraph.strip():
            lines.append("") 
            continue
        current_line = ""
        for word in paragraph.split(' '):
            test_line = current_line + word + " "
            w = dummy_draw.textlength(test_line, font=font)
            if w <= max_text_width: current_line = test_line
            else:
                if current_line: lines.append(current_line)
                current_line = word + " "
        if current_line: lines.append(current_line)

    text_color = COLORS[ud['color']]['rgb']
    image_paths = []
    page_num = 1
    image, draw = create_new_page(ud['paper'], img_width, img_height, font_size, line_spacing)
    y_text = 120
    
    for line in lines:
        if y_text + line_spacing > max_y:
            out_path = os.path.join(TEMP_DIR, f"draft_{chat_id}_p{page_num}_{int(time.time())}.png")
            image.save(out_path)
            image_paths.append(out_path)
            if progress_callback: progress_callback(page_num)
            page_num += 1
            image, draw = create_new_page(ud['paper'], img_width, img_height, font_size, line_spacing)
            y_text = 120
            
        if line == "":
            y_text += line_spacing
            continue

        current_x = left_margin + random.randint(-5, 8) 
        for word in line.split(' '):
            if not word: continue
            y_offset = random.randint(-2, 2)
            draw.text((current_x, y_text + y_offset), word, font=font, fill=text_color)
            current_x += dummy_draw.textlength(word, font=font) + dummy_draw.textlength(" ", font=font) + random.randint(-2, 4)
        y_text += line_spacing + random.randint(-3, 3)

    out_path = os.path.join(TEMP_DIR, f"draft_{chat_id}_p{page_num}_{int(time.time())}.png")
    image.save(out_path)
    image_paths.append(out_path)
    if progress_callback: progress_callback(page_num)
    return image_paths

def create_pdf_from_images(image_paths, chat_id):
    pdf = FPDF(unit="pt", format=[1240, 1754])
    for img_path in image_paths:
        pdf.add_page()
        pdf.image(img_path, 0, 0, 1240, 1754)
    pdf_path = os.path.join(TEMP_DIR, f"document_{chat_id}_{int(time.time())}.pdf")
    pdf.output(pdf_path)
    return pdf_path

def extract_text_from_file(file_path, file_ext):
    extracted_text = ""
    try:
        if file_ext == '.pdf':
            with open(file_path, 'rb') as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                for page in reader.pages:
                    extracted_text += page.extract_text() + "\n"
        elif file_ext == '.docx':
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                extracted_text += para.text + "\n"
    except Exception: pass
    return extracted_text.strip()

def send_admin_menu(chat_id):
    ud = init_user(chat_id)
    ud['admin_state'] = None
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(KeyboardButton("🔤 Кор бо шрифтҳо"))
    if chat_id == ADMIN_ID:
        markup.add(KeyboardButton("👥 Идоракунии админҳо"))
        markup.add(KeyboardButton("📢 Обунаи маҷбурӣ"))
    markup.add(KeyboardButton(BTN_MAIN_BACK))
    bot.send_message(chat_id, "🛠 **Панели Асосии Админ**", parse_mode="Markdown", reply_markup=markup)

# ==========================================
# 5. ҲАНДЛЕРҲОИ БОТ
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if not enforce_subscription(message.chat.id): return
    ud = init_user(message.chat.id)
    ud['admin_state'], ud['user_state'], ud['content'] = None, None, None
    text = (
        "👋 Салом! Ба боти **Реферат Дастнавис** хуш омадед!\n\n"
        "Шумо метавонед матни оддӣ ё файлҳои **PDF** ва **Word (.docx)**-ро ба ман фиристед.\n"
        "👇 *Лутфан аввал матн ё файли худро равон кунед:*"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())

@bot.message_handler(commands=['admin'])
def admin_panel_cmd(message):
    chat_id = message.chat.id
    if chat_id != ADMIN_ID and chat_id not in SUB_ADMINS:
        bot.send_message(chat_id, "⛔️ Шумо ба ин бахш дастрасӣ надоред.")
        return
    send_admin_menu(chat_id)

@bot.message_handler(content_types=['document'])
def handle_document(message):
    chat_id = message.chat.id
    if not enforce_subscription(chat_id): return
    ud = init_user(chat_id)
    file_name = message.document.file_name.lower()
    
    if ud.get('admin_state') == 'wait_font_file' and (chat_id == ADMIN_ID or chat_id in SUB_ADMINS):
        if not (file_name.endswith('.ttf') or file_name.endswith('.otf')):
            bot.send_message(chat_id, "⚠️ Лутфан танҳо файли `.ttf` ё `.otf` равон кунед.")
            return
        msg = bot.send_message(chat_id, "⏳ Шрифт боргирӣ шуда истодааст...")
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            save_path = os.path.join(FONTS_DIR, message.document.file_name)
            with open(save_path, 'wb') as new_file: new_file.write(downloaded_file)
            FONTS[ud['temp_data']] = message.document.file_name
            save_json(FONTS_FILE, FONTS)
            bot.delete_message(chat_id, msg.message_id)
            bot.send_message(chat_id, f"🎉 Шрифти **{ud['temp_data']}** илова шуд!")
            send_admin_menu(chat_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Хатогӣ: {e}", chat_id, msg.message_id)
        return

    if not (file_name.endswith('.pdf') or file_name.endswith('.docx')):
        bot.send_message(chat_id, "⚠️ Лутфан танҳо файлҳои PDF ё Word (.docx) равон кунед.")
        return

    msg = bot.send_message(chat_id, "⏳ Файл боргирӣ шуда истодааст...")
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        ext = '.pdf' if file_name.endswith('.pdf') else '.docx'
        temp_path = os.path.join(TEMP_DIR, f"input_{chat_id}{ext}")
        with open(temp_path, 'wb') as new_file: new_file.write(downloaded_file)
        extracted_text = extract_text_from_file(temp_path, ext)
        os.remove(temp_path) 
        if not extracted_text:
            bot.edit_message_text("❌ Матн аз ин файл ёфт нашуд.", chat_id, msg.message_id)
            return
        ud['content'] = extracted_text
        bot.delete_message(chat_id, msg.message_id)
        send_dashboard(chat_id, "✅ Файл қабул шуд ва матн ҷудо карда шуд!\nАкнун танзимотро иваз кунед ё '✅ ТАВЛИД КАРДАН'-ро пахш намоед.")
    except Exception as e:
        bot.edit_message_text(f"❌ Хатогӣ: {e}", chat_id, msg.message_id)

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text.startswith('/'): return
    chat_id = message.chat.id
    if not enforce_subscription(chat_id): return
    
    text = message.text.strip()
    ud = init_user(chat_id)
    
    # === НАВИГАТСИЯ ===
    if text == BTN_MAIN_BACK:
        ud['user_state'], ud['admin_state'] = None, None
        send_dashboard(chat_id) if ud.get('content') else bot.send_message(chat_id, "Хуш омадед! Матн равон кунед.", reply_markup=ReplyKeyboardRemove())
        return
        
    if text == BTN_ADMIN_BACK: # ХАТОГӢ ДАР ҲАМИН ҶО ИСЛОҲ ШУД
        send_admin_menu(chat_id)
        return

    if text == BTN_BACK:
        ud['user_state'] = None
        send_dashboard(chat_id)
        return

    # === МЕНЮҲОИ АДМИН ===
    if text == "🔤 Кор бо шрифтҳо" and (chat_id == ADMIN_ID or chat_id in SUB_ADMINS):
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(KeyboardButton("➕ Иловаи Шрифт"), KeyboardButton("➖ Нест кардани Шрифт"))
        markup.add(KeyboardButton(BTN_ADMIN_BACK))
        bot.send_message(chat_id, "🔤 **Бахши Шрифтҳо**", parse_mode="Markdown", reply_markup=markup)
        return

    if text == "👥 Идоракунии админҳо" and chat_id == ADMIN_ID:
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(KeyboardButton("➕ Иловаи Админ"), KeyboardButton("➖ Нест кардани Админ"))
        markup.add(KeyboardButton(BTN_ADMIN_BACK))
        bot.send_message(chat_id, "👥 **Бахши Админҳо**", parse_mode="Markdown", reply_markup=markup)
        return

    if text == "📢 Обунаи маҷбурӣ" and chat_id == ADMIN_ID:
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(KeyboardButton("➕ Иловаи Канал"), KeyboardButton("➖ Нест кардани Канал"))
        markup.add(KeyboardButton(BTN_ADMIN_BACK))
        
        ch_list = "\n".join([f"• {ch}" for ch in CHANNELS.keys()]) if CHANNELS else "Ягон канал нест."
        bot.send_message(chat_id, f"📢 **Бахши Обунаи Маҷбурӣ**\n\nКаналҳои ҳозира:\n{ch_list}", parse_mode="Markdown", reply_markup=markup)
        return

    # === АМАЛҲОИ АДМИН (Тугмаҳои дохилӣ) ===
    if text == "➕ Иловаи Шрифт" and (chat_id == ADMIN_ID or chat_id in SUB_ADMINS):
        ud['admin_state'] = 'wait_font_name'
        markup = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton(BTN_ADMIN_BACK))
        bot.send_message(chat_id, "✍️ Номи шрифти навро нависед:", reply_markup=markup)
        return

    if text == "➖ Нест кардани Шрифт" and (chat_id == ADMIN_ID or chat_id in SUB_ADMINS):
        ud['admin_state'] = 'wait_del_font'
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for name in FONTS.keys(): markup.add(KeyboardButton(f"🗑 {name}"))
        markup.add(KeyboardButton(BTN_ADMIN_BACK))
        bot.send_message(chat_id, "Кадом шрифтро нест кардан мехоҳед?", reply_markup=markup)
        return

    if text == "➕ Иловаи Админ" and chat_id == ADMIN_ID:
        ud['admin_state'] = 'wait_admin_id'
        markup = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton(BTN_ADMIN_BACK))
        bot.send_message(chat_id, "✍️ ID-и корбарро нависед:", reply_markup=markup)
        return

    if text == "➖ Нест кардани Админ" and chat_id == ADMIN_ID:
        ud['admin_state'] = 'wait_del_admin'
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for s_id in SUB_ADMINS: markup.add(KeyboardButton(f"❌ {s_id}"))
        markup.add(KeyboardButton(BTN_ADMIN_BACK))
        bot.send_message(chat_id, "Кадом админро аз вазифа озод мекунем?", reply_markup=markup)
        return

    if text == "➕ Иловаи Канал" and chat_id == ADMIN_ID:
        ud['admin_state'] = 'wait_channel_id'
        markup = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton(BTN_ADMIN_BACK))
        bot.send_message(chat_id, "✍️ Username-и каналро нависед (масалан: `@it_tojik`).\n\n⚠️ *Огоҳӣ: Бот бояд ҳатман дар он канал Админ бошад, вагарна илова карда намешавад!*", parse_mode="Markdown", reply_markup=markup)
        return

    if text == "➖ Нест кардани Канал" and chat_id == ADMIN_ID:
        ud['admin_state'] = 'wait_del_channel'
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for ch in CHANNELS.keys(): markup.add(KeyboardButton(f"🗑 {ch}"))
        markup.add(KeyboardButton(BTN_ADMIN_BACK))
        bot.send_message(chat_id, "Кадом каналро аз рӯйхат нест кунем?", reply_markup=markup)
        return

    # === ҲОЛАТҲОИ ИНТИЗОРИИ АДМИН (States) ===
    if ud.get('admin_state') == 'wait_font_name':
        if text in FONTS:
            bot.send_message(chat_id, "⚠️ Ин ном аллакай ҳаст. Дигар ном нависед:")
            return
        ud['temp_data'] = text
        ud['admin_state'] = 'wait_font_file'
        bot.send_message(chat_id, f"✅ Ном қабул шуд: **{text}**\nАкнун файли `.ttf` ё `.otf` равон кунед:", parse_mode="Markdown")
        return

    if ud.get('admin_state') == 'wait_del_font':
        name = text.replace("🗑 ", "")
        if name in FONTS:
            try: os.remove(os.path.join(FONTS_DIR, FONTS[name]))
            except: pass
            del FONTS[name]
            save_json(FONTS_FILE, FONTS)
            bot.send_message(chat_id, f"✅ Шрифти '{name}' нест шуд!")
            send_admin_menu(chat_id)
        return

    if ud.get('admin_state') == 'wait_admin_id' and chat_id == ADMIN_ID:
        try:
            new_id = int(text)
            if new_id not in SUB_ADMINS and new_id != ADMIN_ID:
                SUB_ADMINS.append(new_id)
                save_json(ADMINS_FILE, SUB_ADMINS)
                bot.send_message(chat_id, f"✅ Админи нав илова шуд!")
            else:
                bot.send_message(chat_id, "⚠️ Ин ID аллакай админ аст.")
        except: bot.send_message(chat_id, "⚠️ Фақат рақам нависед.")
        send_admin_menu(chat_id)
        return

    if ud.get('admin_state') == 'wait_del_admin' and chat_id == ADMIN_ID:
        del_id = int(text.replace("❌ ", "")) if text.replace("❌ ", "").isdigit() else 0
        if del_id in SUB_ADMINS:
            SUB_ADMINS.remove(del_id)
            save_json(ADMINS_FILE, SUB_ADMINS)
            bot.send_message(chat_id, "✅ Админ нест карда шуд!")
        send_admin_menu(chat_id)
        return

    if ud.get('admin_state') == 'wait_channel_id' and chat_id == ADMIN_ID:
        ch_id = text
        msg = bot.send_message(chat_id, "⏳ Санҷиши ҳуқуқҳои бот дар канал...")
        try:
            bot.get_chat_member(ch_id, ADMIN_ID) 
            ud['temp_data'] = ch_id
            ud['admin_state'] = 'wait_channel_link'
            bot.edit_message_text(f"✅ Бот ба канал дастрасӣ дорад!\n\nАкнун **ссылкаи ин каналро** (масалан: `https://t.me/...`) равон кунед, то корбарон ба он даромада тавонанд:", chat_id, msg.message_id, parse_mode="Markdown")
        except Exception as e:
            bot.edit_message_text(f"❌ Хатогӣ! Бот дар канали `{ch_id}` админ нест ё номи канал нодуруст аст.\nАввал ботро дар канал админ кунед ва аз нав кӯшиш кунед.", chat_id, msg.message_id, parse_mode="Markdown")
        return

    if ud.get('admin_state') == 'wait_channel_link' and chat_id == ADMIN_ID:
        ch_link = text
        CHANNELS[ud['temp_data']] = ch_link
        save_json(CHANNELS_FILE, CHANNELS)
        bot.send_message(chat_id, f"🎉 Канали {ud['temp_data']} бо муваффақият ба обунаи маҷбурӣ илова шуд!")
        send_admin_menu(chat_id)
        return

    if ud.get('admin_state') == 'wait_del_channel' and chat_id == ADMIN_ID:
        ch_id = text.replace("🗑 ", "")
        if ch_id in CHANNELS:
            del CHANNELS[ch_id]
            save_json(CHANNELS_FILE, CHANNELS)
            bot.send_message(chat_id, "✅ Канал аз рӯйхат хориҷ шуд!")
        send_admin_menu(chat_id)
        return

    # === МЕНЮИ АСОСИИ КОРБАР ===
    if text == BTN_FORMAT:
        ud['user_state'] = 'wait_format'
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(KeyboardButton("📄 PDF"), KeyboardButton("🖼 Расм (PNG)"))
        markup.add(KeyboardButton(BTN_BACK))
        bot.send_message(chat_id, "👇 Намуди формати натиҷаро интихоб кунед:", reply_markup=markup)
        return

    if text == BTN_FONT:
        ud['user_state'] = 'wait_font'
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for name in FONTS.keys(): markup.add(KeyboardButton(f"🖋 {name}"))
        markup.add(KeyboardButton(BTN_BACK))
        bot.send_message(chat_id, "👇 Шрифти худро интихоб кунед:", reply_markup=markup)
        return

    if text == BTN_COLOR:
        ud['user_state'] = 'wait_color'
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for code, info in COLORS.items(): markup.add(KeyboardButton(f"🎨 {info['name']}"))
        markup.add(KeyboardButton(BTN_BACK))
        bot.send_message(chat_id, "👇 Ранги қаламро интихоб кунед:", reply_markup=markup)
        return

    if text == BTN_PAPER:
        ud['user_state'] = 'wait_paper'
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for code, name in PAPERS.items(): markup.add(KeyboardButton(f"📔 {name}"))
        markup.add(KeyboardButton(BTN_BACK))
        bot.send_message(chat_id, "👇 Намуди варақаро интихоб кунед:", reply_markup=markup)
        return

    if text == BTN_GENERATE:
        if not FONTS:
            bot.send_message(chat_id, "⚠️ Шрифтҳо аз тарафи админ тоза карда шудаанд!")
            return
        if not ud.get('content'):
            bot.send_message(chat_id, "⚠️ Лутфан аввал матн ё файл равон кунед!")
            return
            
        progress_msg = bot.send_message(chat_id, "⚙️ Дастнавис тавлид шуда истодааст... Лутфан интизор шавед ⏳", reply_markup=ReplyKeyboardRemove())
        def update_progress(page):
            try: bot.edit_message_text(f"⏳ **Саҳифаи {page} омода шуд...**", chat_id, progress_msg.message_id, parse_mode="Markdown")
            except: pass 

        try:
            img_paths = generate_handwritten_images(chat_id, progress_callback=update_progress)
            bot.delete_message(chat_id, progress_msg.message_id)
            
            if ud.get('format', 'pdf') == 'pdf':
                pdf_path = create_pdf_from_images(img_paths, chat_id)
                with open(pdf_path, 'rb') as doc: bot.send_document(chat_id, doc, caption="📄 Натиҷа (PDF)")
                if os.path.exists(pdf_path): os.remove(pdf_path)
            else:
                bot.send_message(chat_id, "🖼 Натиҷа дар намуди расмҳо:")
                for img_path in img_paths:
                    with open(img_path, 'rb') as photo: bot.send_photo(chat_id, photo)
                
            send_dashboard(chat_id, "🎉 Файл омода шуд!\nАгар лозим бошад, метавонед танзимотро иваз карда, дубора '✅ ТАВЛИД КАРДАН'-ро пахш кунед:")
            for img in img_paths:
                if os.path.exists(img): os.remove(img)
        except Exception as e:
            bot.send_message(chat_id, f"❌ Хатогии дохилӣ: {e}")
            send_dashboard(chat_id)
        return

    # === ҲОЛАТҲОИ ИНТИХОБИ КОРБАР ===
    if ud.get('user_state') == 'wait_format':
        if text == "📄 PDF":
            ud['format'] = 'pdf'
            ud['user_state'] = None
            send_dashboard(chat_id, "✅ Формати **PDF** интихоб шуд!")
        elif text == "🖼 Расм (PNG)":
            ud['format'] = 'images'
            ud['user_state'] = None
            send_dashboard(chat_id, "✅ Формати **Расм (PNG)** интихоб шуд!")
        else:
            bot.send_message(chat_id, "⚠️ Лутфан аз тугмаҳои поён интихоб кунед.")
        return

    if ud.get('user_state') == 'wait_font':
        name = text.replace("🖋 ", "")
        if name in FONTS:
            ud['font_name'], ud['font_file'], ud['user_state'] = name, FONTS[name], None
            send_dashboard(chat_id, f"✅ Шрифти **{name}** интихоб шуд!")
        else: bot.send_message(chat_id, "⚠️ Лутфан аз тугмаҳои поён интихоб кунед.")
        return

    if ud.get('user_state') == 'wait_color':
        name = text.replace("🎨 ", "")
        for code, info in COLORS.items():
            if info['name'] == name:
                ud['color'], ud['user_state'] = code, None
                send_dashboard(chat_id, f"✅ Ранги **{info['name']}** интихоб шуд!")
                return
        bot.send_message(chat_id, "⚠️ Лутфан аз тугмаҳои поён интихоб кунед.")
        return

    if ud.get('user_state') == 'wait_paper':
        name = text.replace("📔 ", "")
        for code, p_name in PAPERS.items():
            if p_name == name:
                ud['paper'], ud['user_state'] = code, None
                send_dashboard(chat_id, f"✅ Варақаи **{p_name}** интихоб шуд!")
                return
        bot.send_message(chat_id, "⚠️ Лутфан аз тугмаҳои поён интихоб кунед.")
        return

    # ҚАБУЛИ МАТНИ ОДДӢ
    ud['content'] = text
    send_dashboard(chat_id, "✅ Матн қабул шуд!\nАкнун метавонед танзимотро иваз кунед ё '✅ ТАВЛИД КАРДАН'-ро пахш намоед.")

if __name__ == "__main__":
    print("🤖 Боти 'Реферат Дастнавис' фаъол шуд...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)