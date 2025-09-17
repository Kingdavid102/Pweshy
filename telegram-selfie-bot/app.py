import os
import logging
from telegram import Update, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from rembg import remove
from PIL import Image
import io

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Your bot token from BotFather (will be set as environment variable)
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
PORT = int(os.environ.get('PORT', 8443))

# Store user data temporarily
user_data = {}

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hi! Send me your selfie first, then send the background image.')

def handle_photo(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    photo_file = update.message.photo[-1].get_file()

    # Check if this is the first or second photo
    if user_id not in user_data:
        user_data[user_id] = {'selfie': None, 'background': None}

    # Download the photo into memory
    bio = io.BytesIO()
    photo_file.download(out=bio)
    bio.seek(0)

    if user_data[user_id]['selfie'] is None:
        # This is the selfie
        user_data[user_id]['selfie'] = bio
        update.message.reply_text("Great selfie! Now send the background picture.")
    else:
        # This is the background
        user_data[user_id]['background'] = bio
        update.message.reply_text("Got it! Processing your image, please wait... (this may take a while on free servers)")

        # Process the images
        try:
            output_bio = process_images(user_data[user_id]['selfie'], user_data[user_id]['background'])
            # Send the final image
            context.bot.send_photo(chat_id=update.effective_chat.id, photo=InputFile(output_bio, filename='night_selfie.png'))
            update.message.reply_text("Here you go! 🎉")
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            update.message.reply_text("Sorry, something went wrong. I might be out of memory. Try again in a minute.")
        finally:
            # Clean up user data
            del user_data[user_id]

def process_images(selfie_bio, background_bio):
    """Remove background from selfie and composite it onto the background image"""
    # Remove background from selfie
    selfie_bio.seek(0)
    input_data = selfie_bio.read()
    output_data = remove(input_data)  # This is the slow, CPU-intensive step
    removed_bg_image = Image.open(io.BytesIO(output_data))

    # Open the background image
    background_bio.seek(0)
    background_image = Image.open(background_bio).convert('RGBA')

    # Resize images to fit (simple version: resize selfie to fit background width)
    bg_width, bg_height = background_image.size
    removed_bg_image.thumbnail((bg_width, bg_height))

    # Calculate position to center the selfie
    paste_x = (bg_width - removed_bg_image.width) // 2
    paste_y = (bg_height - removed_bg_image.height) // 2

    # Composite the images
    composite = background_image.copy()
    composite.paste(removed_bg_image, (paste_x, paste_y), removed_bg_image)

    # Save the final image to a BytesIO object
    output_bio = io.BytesIO()
    composite.save(output_bio, format='PNG')
    output_bio.seek(0)

    return output_bio

def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.photo & ~Filters.command, handle_photo))

    # Start the Bot on Heroku
    updater.start_webhook(listen="0.0.0.0",
                          port=PORT,
                          url_path=TOKEN,
                          webhook_url=f"https://pweshy-stuff-ba7d1a1bd9f5.herokuapp.com/{TOKEN}")

    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()
