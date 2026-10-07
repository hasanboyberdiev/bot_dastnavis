import os
import json
import textwrap
import random
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
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

# ==========================================
# 2. МЕНЕҶЕРИ ШРИФТҲО ВА АДМИНҲО
# ==========================================
DEFAULT_FONTS = {}

def load_fonts():
    if os.path.exists(FONTS_FILE):
        with open(FONTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        with open(FONTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_FONTS, f, ensure_ascii=False, indent=4)
        return DEFAULT_FONTS

def save_fonts():
    with open(FONTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(FONTS, f, ensure_ascii=False, indent=4)

def load_admins():
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)
        return []

def save_admins():
    with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
        json.dump(SUB_ADMINS, f, ensure_ascii=False, indent=4)

FONTS = load_fonts()
SUB_ADMINS = load_admins()

# ==========================================
# 3. ФУНКСИЯҲОИ КОРБАР ВА ИНТЕРФЕЙСИ НАВ (InlineKeyboardMarkup)
# ==========================================
def init_user(chat_id):
    first_font_name = list(FONTS.keys())[0] if FONTS else "Default"
    first_font_file = FONTS.get(first_font_name, "")
    
    if chat_id not in user_data:
        user_data[chat_id] = {
            'font_name': first_font_name,
            'font_file': first_font_file,
            'color': 'blue',
            'paper': 'lined',
            'format': 'pdf', 
            'content': None,
            'admin_state': None,
            'temp_font_name': None
        }
    else:
        if user_data[chat_id]['font_name'] not in FONTS and FONTS:
            user_data[chat_id]['font_name'] = first_font_name
            user_data[chat_id]['font_file'] = first_font_file
            
    return user_data[chat_id]

def get_dashboard_menu(chat_id):
    ud = init_user(chat_id)
    markup = InlineKeyboardMarkup(row_width=2)
    
    font_display = ud['font_name'] if FONTS else "Шрифт нест ❌"
    format_display = "PDF 📄" if ud.get('format', 'pdf') == 'pdf' else "Расмҳо 🖼"
    
    # Қатори 1: Шрифт (Калон)
    markup.add(InlineKeyboardButton(f"🔤 Шрифт: {font_display}", callback_data="menu_font"))
    
    # Қатори 2: Ранг ва Варақа (Дар як сатр)
    markup.row(
        InlineKeyboardButton(f"🎨 Ранг: {COLORS[ud['color']]['name']}", callback_data="menu_color"),
        InlineKeyboardButton(f"📔 Варақа: {PAPERS[ud['paper']]}", callback_data="menu_paper")
    )
    
    # Қатори 3: Формати натиҷа
    markup.add(InlineKeyboardButton(f"💾 Формати натиҷа: {format_display}", callback_data="toggle_format"))
    
    # Қатори 4: Тугмаи Асосӣ
    markup.add(InlineKeyboardButton("✅ ТАВЛИД КАРДАН", callback_data="action_generate"))
    
    return markup

def get_options_menu(option_type):
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    
    if option_type == 'font':
        for name, file in FONTS.items():
            buttons.append(InlineKeyboardButton(name, callback_data=f"set_font_{name}"))
        markup.add(*buttons)
    elif option_type == 'color':
        for code, info in COLORS.items():
            buttons.append(InlineKeyboardButton(info['name'], callback_data=f"set_color_{code}"))
        markup.add(*buttons)
    elif option_type == 'paper':
        for code, name in PAPERS.items():
            buttons.append(InlineKeyboardButton(name, callback_data=f"set_paper_{code}"))
        markup.add(*buttons)
            
    markup.add(InlineKeyboardButton("⬅️ Бозгашт ба Меню", callback_data="menu_dashboard"))
    return markup

def send_dashboard(chat_id, message_id=None, custom_text=None):
    text = custom_text if custom_text else "⚙️ **Танзимоти Дастнависи шумо:**\nХусусиятҳоро тағйир диҳед ё тугмаи 'Тавлид кардан'-ро пахш кунед:"
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=get_dashboard_menu(chat_id))
    else:
        bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=get_dashboard_menu(chat_id))

# ==========================================
# 4. ФУНКСИЯҲОИ ГЕНЕРАТСИЯ
# ==========================================
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
    
    font_size = 40 
    line_spacing = 55 
    
    img_width, img_height = 1240, 1754 
    left_margin = 130 
    right_margin = 80
    max_text_width = img_width - left_margin - right_margin
    bottom_margin = 150 
    max_y = img_height - bottom_margin
    
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        font = ImageFont.load_default()

    dummy_img = Image.new('RGB', (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    
    lines = []
    for paragraph in text.split('\n'):
        if not paragraph.strip():
            lines.append("") 
            continue
        words = paragraph.split(' ')
        current_line = ""
        for word in words:
            test_line = current_line + word + " "
            w = dummy_draw.textlength(test_line, font=font)
            if w <= max_text_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word + " "
        if current_line:
            lines.append(current_line)

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
            
            if progress_callback:
                progress_callback(page_num)
                
            page_num += 1
            image, draw = create_new_page(ud['paper'], img_width, img_height, font_size, line_spacing)
            y_text = 120
            
        if line == "":
            y_text += line_spacing
            continue

        words = line.split(' ')
        current_x = left_margin + random.randint(-5, 8) 
        
        for word in words:
            if not word: continue
            y_offset = random.randint(-2, 2)
            draw.text((current_x, y_text + y_offset), word, font=font, fill=text_color)
            
            word_w = dummy_draw.textlength(word, font=font)
            space_w = dummy_draw.textlength(" ", font=font)
            current_x += word_w + space_w + random.randint(-2, 4)

        y_text += line_spacing + random.randint(-3, 3)

    out_path = os.path.join(TEMP_DIR, f"draft_{chat_id}_p{page_num}_{int(time.time())}.png")
    image.save(out_path)
    image_paths.append(out_path)
    
    if progress_callback:
        progress_callback(page_num)
        
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
    except Exception as e:
        pass
    return extracted_text.strip()

# ==========================================
# 5. ҲАНДЛЕРҲОИ БОТ
# ==========================================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    chat_id = message.chat.id
    if chat_id != ADMIN_ID and chat_id not in SUB_ADMINS:
        bot.send_message(chat_id, "⛔️ Шумо ба ин бахш дастрасӣ надоред.")
        return
        
    init_user(chat_id)['admin_state'] = None
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("➕ Илова кардани Шрифт", callback_data="admin_add_font"),
        InlineKeyboardButton("➖ Нест кардани Шрифт", callback_data="admin_del_list")
    )
    
    if chat_id == ADMIN_ID:
        markup.add(InlineKeyboardButton("👥 Идоракунии Админҳо", callback_data="admin_manage_admins"))
        
    bot.send_message(chat_id, "🛠 **Панели Админ**\nЛутфан амалро интихоб кунед:", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    ud = init_user(message.chat.id)
    ud['admin_state'] = None
    text = (
        "👋 Салом! Ба боти **Реферат Дастнавис** хуш омадед!\n\n"
        "Шумо метавонед матни оддӣ ё файлҳои **PDF** ва **Word (.docx)**-ро ба ман фиристед.\n"
        "👇 *Ҳоло ягон матн ё файл равон кунед:*"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text.startswith('/'): return
    chat_id = message.chat.id
    ud = init_user(chat_id)
    
    if ud.get('admin_state') == 'wait_font_name' and (chat_id == ADMIN_ID or chat_id in SUB_ADMINS):
        font_name = message.text.strip()
        if font_name in FONTS:
            bot.send_message(chat_id, "⚠️ Ин ном аллакай вуҷуд дорад. Номи дигар нависед:")
            return
        ud['temp_font_name'] = font_name
        ud['admin_state'] = 'wait_font_file'
        bot.send_message(chat_id, f"✅ Ном қабул шуд: **{font_name}**\n\nАкнун файли шрифтро (формати `.ttf` ё `.otf`) ба ман равон кунед:", parse_mode="Markdown")
        return

    if ud.get('admin_state') == 'wait_admin_id' and chat_id == ADMIN_ID:
        try:
            new_admin_id = int(message.text.strip())
            if new_admin_id not in SUB_ADMINS and new_admin_id != ADMIN_ID:
                SUB_ADMINS.append(new_admin_id)
                save_admins()
                bot.send_message(chat_id, f"✅ Админи нав бо ID `{new_admin_id}` бо муваффақият илова шуд!", parse_mode="Markdown")
            else:
                bot.send_message(chat_id, "⚠️ Ин ID аллакай дар рӯйхати админҳо вуҷуд дорад.")
        except ValueError:
            bot.send_message(chat_id, "⚠️ Хатогӣ! Лутфан танҳо рақамҳои ID-ро нависед (масалан: 123456789).")
        
        ud['admin_state'] = None
        return

    ud['content'] = message.text
    send_dashboard(chat_id)

@bot.message_handler(content_types=['document'])
def handle_document(message):
    chat_id = message.chat.id
    ud = init_user(chat_id)
    file_name = message.document.file_name.lower()
    
    if ud.get('admin_state') == 'wait_font_file' and (chat_id == ADMIN_ID or chat_id in SUB_ADMINS):
        if not (file_name.endswith('.ttf') or file_name.endswith('.otf')):
            bot.send_message(chat_id, "⚠️ Лутфан танҳо файли формати `.ttf` ё `.otf` равон кунед.", parse_mode="Markdown")
            return
            
        msg = bot.send_message(chat_id, "⏳ Шрифт боргирӣ шуда истодааст...")
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            save_path = os.path.join(FONTS_DIR, message.document.file_name)
            with open(save_path, 'wb') as new_file:
                new_file.write(downloaded_file)
                
            FONTS[ud['temp_font_name']] = message.document.file_name
            save_fonts()
            
            ud['admin_state'] = None
            bot.edit_message_text(f"🎉 Шрифти **{ud['temp_font_name']}** бо муваффақият илова шуд!", chat_id, msg.message_id, parse_mode="Markdown")
        except Exception as e:
            bot.edit_message_text(f"❌ Хатогӣ ҳангоми боргирии шрифт: {e}", chat_id, msg.message_id)
        return

    if not (file_name.endswith('.pdf') or file_name.endswith('.docx')):
        bot.send_message(chat_id, "⚠️ Лутфан танҳо файлҳои формати PDF ё Word (.docx) равон кунед.")
        return

    msg = bot.send_message(chat_id, "⏳ Файл боргирӣ шуда истодааст...")
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        ext = '.pdf' if file_name.endswith('.pdf') else '.docx'
        temp_path = os.path.join(TEMP_DIR, f"input_{chat_id}{ext}")
        
        with open(temp_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        extracted_text = extract_text_from_file(temp_path, ext)
        os.remove(temp_path) 
        
        if not extracted_text:
            bot.edit_message_text("❌ Матн аз ин файл ёфт нашуд.", chat_id, msg.message_id)
            return

        ud['content'] = extracted_text
        bot.delete_message(chat_id, msg.message_id)
        send_dashboard(chat_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Хатогӣ: {e}", chat_id, msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data
    ud = init_user(chat_id)
    msg_id = call.message.message_id

    if data == "admin_add_font":
        ud['admin_state'] = 'wait_font_name'
        bot.edit_message_text("✍️ Номи шрифти навро нависед:", chat_id, msg_id, parse_mode="Markdown")
        return
        
    elif data == "admin_del_list":
        markup = InlineKeyboardMarkup(row_width=2)
        if FONTS:
            buttons = [InlineKeyboardButton(f"❌ {name}", callback_data=f"del_font_{name}") for name in FONTS.keys()]
            markup.add(*buttons)
        else:
            markup.add(InlineKeyboardButton("⚠️ Ягон шрифт намондааст", callback_data="none"))
        markup.add(InlineKeyboardButton("⬅️ Бозгашт", callback_data="admin_back"))
        bot.edit_message_text("Кадом шрифтро нест кардан мехоҳед?", chat_id, msg_id, reply_markup=markup)
        return
        
    elif data.startswith("del_font_"):
        font_to_del = data.replace("del_font_", "")
        if font_to_del in FONTS:
            file_to_del = FONTS[font_to_del]
            del FONTS[font_to_del]
            save_fonts()
            try:
                os.remove(os.path.join(FONTS_DIR, file_to_del))
            except:
                pass
            bot.answer_callback_query(call.id, f"Шрифти '{font_to_del}' нест карда шуд!", show_alert=False)
            
            markup = InlineKeyboardMarkup(row_width=2)
            if FONTS:
                buttons = [InlineKeyboardButton(f"❌ {name}", callback_data=f"del_font_{name}") for name in FONTS.keys()]
                markup.add(*buttons)
            else:
                markup.add(InlineKeyboardButton("⚠️ Ягон шрифт намондааст", callback_data="none"))
            markup.add(InlineKeyboardButton("⬅️ Бозгашт", callback_data="admin_back"))
            bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=markup)
        return
        
    elif data == "admin_manage_admins":
        if chat_id != ADMIN_ID: return
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("➕ Иловаи Админ", callback_data="admin_add_sub"),
            InlineKeyboardButton("➖ Нест кардани Админ", callback_data="admin_del_sub_list"),
            InlineKeyboardButton("⬅️ Бозгашт", callback_data="admin_back")
        )
        bot.edit_message_text("👥 **Идоракунии Админҳо**\nДар ин ҷо шумо метавонед админҳои навро илова кунед.", chat_id, msg_id, parse_mode="Markdown", reply_markup=markup)
        return
        
    elif data == "admin_add_sub":
        if chat_id != ADMIN_ID: return
        ud['admin_state'] = 'wait_admin_id'
        bot.edit_message_text("✍️ ID-и корбарро нависед, то ӯро админ таъин кунед:\n*(Шумо метавонед ID-ро аз ботҳои ба монанди @userinfobot гиред)*", chat_id, msg_id, parse_mode="Markdown")
        return
        
    elif data == "admin_del_sub_list":
        if chat_id != ADMIN_ID: return
        markup = InlineKeyboardMarkup(row_width=1)
        if SUB_ADMINS:
            for sub_id in SUB_ADMINS:
                markup.add(InlineKeyboardButton(f"❌ Нест кардан: {sub_id}", callback_data=f"del_sub_{sub_id}"))
        else:
            markup.add(InlineKeyboardButton("⚠️ Ягон админи дигар нест", callback_data="none"))
        markup.add(InlineKeyboardButton("⬅️ Бозгашт", callback_data="admin_manage_admins"))
        bot.edit_message_text("Кадом админро аз вазифа озод кардан мехоҳед?", chat_id, msg_id, reply_markup=markup)
        return
        
    elif data.startswith("del_sub_"):
        if chat_id != ADMIN_ID: return
        sub_id = int(data.replace("del_sub_", ""))
        if sub_id in SUB_ADMINS:
            SUB_ADMINS.remove(sub_id)
            save_admins()
            bot.answer_callback_query(call.id, f"Админ {sub_id} нест карда шуд!", show_alert=False)
            
            markup = InlineKeyboardMarkup(row_width=1)
            if SUB_ADMINS:
                for s_id in SUB_ADMINS:
                    markup.add(InlineKeyboardButton(f"❌ Нест кардан: {s_id}", callback_data=f"del_sub_{s_id}"))
            else:
                markup.add(InlineKeyboardButton("⚠️ Ягон админи дигар нест", callback_data="none"))
            markup.add(InlineKeyboardButton("⬅️ Бозгашт", callback_data="admin_manage_admins"))
            bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=markup)
        return

    elif data == "admin_back":
        admin_panel(call.message)
        return

    if data == "toggle_format":
        ud['format'] = 'images' if ud.get('format', 'pdf') == 'pdf' else 'pdf'
        send_dashboard(chat_id, msg_id)
        return

    if data == "menu_dashboard":
        send_dashboard(chat_id, msg_id)
    elif data.startswith("menu_"):
        if data == "menu_font" and not FONTS:
            bot.answer_callback_query(call.id, "⚠️ Шрифтҳо аз тарафи админ тоза карда шудаанд!", show_alert=True)
            return
            
        option = data.split("_")[1]
        bot.edit_message_text("👇 Интихоб кунед:", chat_id, msg_id, reply_markup=get_options_menu(option))
    
    elif data.startswith("set_font_"):
        font_name = data.replace("set_font_", "")
        if font_name in FONTS:
            ud['font_name'] = font_name
            ud['font_file'] = FONTS[font_name]
        send_dashboard(chat_id, msg_id)
        
    elif data.startswith("set_color_"):
        ud['color'] = data.replace("set_color_", "")
        send_dashboard(chat_id, msg_id)
        
    elif data.startswith("set_paper_"):
        ud['paper'] = data.replace("set_paper_", "")
        send_dashboard(chat_id, msg_id)
        
    elif data == "action_generate":
        if not FONTS:
            bot.answer_callback_query(call.id, "⚠️ Шрифтҳо аз тарафи админ тоза карда шудаанд! Наметавонам тавлид кунам.", show_alert=True)
            return
            
        if not ud.get('content'):
            bot.answer_callback_query(call.id, "⚠️ Матн ёфт нашуд! Лутфан аз нав матн фиристед.", show_alert=True)
            return
            
        progress_msg = bot.edit_message_text("⚙️ Дастнавис тавлид шуда истодааст... Лутфан интизор шавед ⏳", chat_id, msg_id)
        
        def update_progress(page):
            try:
                bot.edit_message_text(f"⏳ **Саҳифаи {page} омода шуд...**", chat_id, progress_msg.message_id, parse_mode="Markdown")
            except:
                pass 

        try:
            img_paths = generate_handwritten_images(chat_id, progress_callback=update_progress)
            bot.delete_message(chat_id, progress_msg.message_id)
            
            if ud.get('format', 'pdf') == 'pdf':
                pdf_path = create_pdf_from_images(img_paths, chat_id)
                with open(pdf_path, 'rb') as doc:
                    bot.send_document(chat_id, doc, caption="📄 Натиҷа дар намуди ҳуҷҷат (PDF)")
                if os.path.exists(pdf_path): os.remove(pdf_path)
            else:
                bot.send_message(chat_id, "🖼 Натиҷа дар намуди расмҳои алоҳида:")
                for img_path in img_paths:
                    with open(img_path, 'rb') as photo:
                        bot.send_photo(chat_id, photo)
                
            edit_text = (
                "🎉 Файл омода шуд!\n\n"
                "✏️ **Тағирот ворид кардан:**\n"
                "Агар лозим бошад, метавонед танзимотро иваз карда, дубора 'ТАВЛИД КАРДАН'-ро пахш кунед:"
            )
            send_dashboard(chat_id, message_id=None, custom_text=edit_text)
            
            for img in img_paths:
                if os.path.exists(img):
                    os.remove(img)
            
        except Exception as e:
            bot.send_message(chat_id, f"❌ Хатогии дохилӣ: {e}")

if __name__ == "__main__":
    print("🤖 Боти 'Реферат Дастнавис' фаъол шуд...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)