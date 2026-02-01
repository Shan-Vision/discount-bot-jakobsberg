import logging
import os
import json
import requests
import asyncio
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    print('❌ BOT_TOKEN не найден!')
    exit(1)
print(f'✅ TOKEN OK: {TOKEN[:10]}...')
PRODUCTS_FILE = 'products.json'
STORES = {
    '🟠 Willys Jakobsberg (Nettovägen 2)': 'https://www.willys.se/erbjudanden/ehandel',
    '🔵 Willys Barkarby': 'https://www.willys.se/erbjudanden/butik',
    '🟢 Maxi ICA Barkarbystaden': 'https://www.ica.se/erbjudanden/maxi-ica-stormarknad-barkarbystaden-1003408/',
    '🟡 ICA Supermarket Hässelby Torg': 'https://www.ica.se/erbjudanden/ica-supermarket-hasselby-torg-1004531/',
    '🔴 Hemköp Jakobsbergs Centrum': 'https://www.hemkop.se/butik/4119/',
    '🟣 Coop Järfälla (Veckovägen)': 'https://www.coop.se/butiker/coop-jarfalla',
    '⚫ Lidl Hässelby (Lövkojsgränd)': 'https://www.lidl.se/s/sv-SE/butiker/haesselby/loevkojsgraend-12/',
    '⚪ Lidl Barkarby (Enköpingsvägen)': 'https://www.lidl.se/c/oerbjudanden/a10000000/',
    '🗡 Matvärlden Veddesta (ближайшая)': 'https://www.matvarlden.se/'  # Общий, локальные через matpriskollen
}

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('✅ Панда! Охотник на скидки!\n'
'/add_list mjölk,bröd\n'
'/list /remove /clear\n'
'/stores /check /check_all'
)

async def add_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products = ' '.join(context.args)
    if not products:
        await update.message.reply_text('Пример: /add_list mjölk,bröd,ost')
        return
    data = json.load(open(PRODUCTS_FILE)) if os.path.exists(PRODUCTS_FILE) else []
    data.extend([p.lower().strip() for p in products.split(',')])
    json.dump(list(set(data)), open(PRODUCTS_FILE, 'w'))
    await update.message.reply_text(f'✅ Добавлено: {products}\nВсего продуктов: {len(data)}')

async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists(PRODUCTS_FILE):
        await update.message.reply_text('Список пуст. /add_list')
        return
    data = json.load(open(PRODUCTS_FILE))
    await update.message.reply_text(f'📋 Твой список ({len(data)}):\n' + '\n'.join(data[-10:]))

async def check_discounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists(PRODUCTS_FILE):
        await update.message.reply_text('Добавь продукты: /add_list')
        return
    
    products = [p for p in json.load(open(PRODUCTS_FILE))]
    await update.message.reply_text('🔍 Проверяю Willys...')
    
    # Willys Jakobsberg
    url = 'https://www.willys.se/erbjudanden/ehandel'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        deals = []
        for item in soup.find_all(['h3', 'h4', 'a', 'span', 'div'], attrs={'class': True}):
            text = item.get_text(strip=True).lower()
            if len(text) > 3 and any(word in text for word in ['kr', '%', 'erbjudande']):
                deals.append(text)
                if len(deals) >= 30: break
        
        matches = [p for p in products if any(p in deal for deal in deals)]
        if matches:
            msg = '🔥 НАЙДЕНЫ СКИДКИ Willys Jakobsberg:\n\n'
            for match in matches[:8]:
                msg += f'• {match.capitalize()}\n'
            msg += '\n👉 willys.se/erbjudanden'
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text('😔 Нет скидок по твоему списку сегодня.\nПопробуй /add_list больше продуктов!')
            
    except Exception as e:
        await update.message.reply_text(f'❌ Ошибка проверки: {str(e)[:80]}\nWillys сайт недоступен.')

  
    
async def check_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /check_all — все 9 магазинов Jakobsberg/Hässelby/Barkarby """
    if not os.path.exists(PRODUCTS_FILE):
        await update.message.reply_text('Добавь продукты: /add_list')
        return
    
    await update.message.reply_text('🔍 Проверяю 9 магазинов...')
    products = [p.lower() for p in json.load(open(PRODUCTS_FILE))]
    all_matches = {}
    
    for name, url in STORES.items():
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            resp = requests.get(url, headers=headers, timeout=12)
            soup = BeautifulSoup(resp.text, 'html.parser')
            deals = []
            for item in soup.find_all(['h1','h2','h3','h4','a','span','div'], attrs={'class': True}):
                text = item.get_text(strip=True).lower()
                if len(text) > 3 and any(w in text for w in ['kr','%', 'rabatt', 'erbjudande', 'pris']):
                    deals.append(text)
                    if len(deals) >= 20: break
            
            matches = [p for p in products if any(p in deal for deal in deals)]
            if matches:
                all_matches[name] = matches[:4]
            print(f'{name}: {len(matches)} совпадений')
        except Exception as e:
            print(f'{name} ошибка: {e}')
        
        await asyncio.sleep(0.7)  # Пауза
    
    if all_matches:
        msg = '🏆 НАЙДЕНЫ СКИДКИ:\n\n'
        for store, matches in list(all_matches.items())[:6]:
            msg += f'{store}:\n' + '\n'.join([f'  • {m.capitalize()}' for m in matches]) + '\n\n'
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text('😔 Нет скидок сегодня.')


async def remove_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /remove mjölk — убрать из списка """
    if not context.args or not os.path.exists(PRODUCTS_FILE):
        await update.message.reply_text('Укажи продукт: /remove mjölk\nИли /list для просмотра')
        return
    
    product = ' '.join(context.args).lower().strip()
    data = json.load(open(PRODUCTS_FILE))
    if product in data:
        data.remove(product)
        json.dump(data, open(PRODUCTS_FILE, 'w'))
        await update.message.reply_text(f'🗑️ Удалено: {product.capitalize()}\nОсталось: {len(data)}')
    else:
        await update.message.reply_text(f'❌ {product.capitalize()} нет в списке:\n' + ', '.join(data[:10]))

async def clear_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /clear — очистить весь список """
    if os.path.exists(PRODUCTS_FILE):
        os.remove(PRODUCTS_FILE)
        await update.message.reply_text('🧹 Список очищен!')
    else:
        await update.message.reply_text('Список уже пуст.')

async def list_stores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /stores — список всех 9 магазинов """
    msg = '🛒 Твои 9 магазинов Jakobsberg/Hässelby/Barkarby:\n\n'
    for i, (name, url) in enumerate(STORES.items(), 1):
        msg += f'{i}. {name}\n   {url.split("/")[2]}\n\n'
    await update.message.reply_text(msg)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_list", add_list))
    app.add_handler(CommandHandler("list", list_products))
    app.add_handler(CommandHandler("check", check_discounts))
    app.add_handler(CommandHandler("check_all", check_all))
    app.add_handler(CommandHandler("remove", remove_product))
    app.add_handler(CommandHandler("clear", clear_list))
    app.add_handler(CommandHandler("stores", list_stores))
    print('🚀 Бот полностью готов! Команды: /start /add_list /list /check')
    app.run_polling()

if __name__ == '__main__':
    main()
