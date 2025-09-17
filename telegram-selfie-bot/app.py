import os
import logging
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from rembg import remove
from PIL import Image
import io

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
PORT = int(os.environ.get('PORT', 8443))
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Hi! Send me your selfie first, then send the background image.')

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    photo_file = await update.message.photo[-1].get_file()

    if user_id not in user_data:
        user_data[user_id] = {'selfie': None, 'background': None}

    bio = io.BytesIO()
    await photo_file.download_to_memory(out=bio)
    bio.seek(0)

    if user_data[user_id]['selfie'] is None:
        user_data[user_id]['selfie'] = bio
        await update.message.reply_text("Great selfie! Now send the background picture.")
    else:
        user_data[user_id]['background'] = bio
        await update.message.reply_text("Got it! Processing... (this may take a while)")

        try:
            output_bio = process_images(user_data[user_id]['selfie'], user_data[user_id]['background'])
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=InputFile(output_bio, filename='night_selfie.png'))
            await update.message.reply_text("Here you go! 🎉")
        except Exception as e:
            logger.error(f"Error: {e}")
            await update.message.reply_text("Sorry, I ran out of memory. Try again in a minute.")
        finally:
            if user_id in user_data:
                del user_data[user_id]

def process_images(selfie_bio, background_bio):
    selfie_bio.seek(0)
    input_data = selfie_bio.read()
    output_data = remove(input_data)
    removed_bg_image = Image.open(io.BytesIO(output_data))

    background_bio.seek(0)
    background_image = Image.open(background_bio).convert('RGBA')

    bg_width, bg_height = background_image.size
    removed_bg_image.thumbnail((bg_width, bg_height))
    paste_x = (bg_width - removed_bg_image.width) // 2
    paste_y = (bg_height - removed_bg_image.height) // 2

    composite = background_image.copy()
    composite.paste(removed_bg_image, (paste_x, paste_y), removed_bg_image)

    output_bio = io.BytesIO()
    composite.save(output_bio, format='PNG')
    output_bio.seek(0)
    return output_bio

def main() -> None:
    """Run the bot."""
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo))

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"https://pweshy-stuff-ba7d1a1bd9f5.herokuapp.com/{TOKEN}"
    )

if __name__ == '__main__':
    main()
