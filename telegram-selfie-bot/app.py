import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from rembg import remove
from PIL import Image
import io

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# Store user data temporarily
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text('Hi! 👋 Send me your selfies first, then send the background image.')

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming photos."""
    try:
        user_id = update.effective_user.id
        photo_file = await update.message.photo[-1].get_file()

        if user_id not in user_data:
            user_data[user_id] = {'selfie': None, 'background': None}
            user_data[user_id]['selfie'] = photo_file
            await update.message.reply_text("✅ Great selfie! Now send the background picture.")
        else:
            user_data[user_id]['background'] = photo_file
            await update.message.reply_text("⏳ Got both images! Processing... (This may take 20-40 seconds)")
            
            # Process the images
            try:
                # Download images
                selfie_bio = io.BytesIO()
                background_bio = io.BytesIO()
                
                await user_data[user_id]['selfie'].download_to_memory(out=selfie_bio)
                await user_data[user_id]['background'].download_to_memory(out=background_bio)
                
                selfie_bio.seek(0)
                background_bio.seek(0)
                
                # Remove background from selfie
                input_data = selfie_bio.read()
                output_data = remove(input_data)
                removed_bg_image = Image.open(io.BytesIO(output_data))

                # Process background image
                background_image = Image.open(background_bio).convert('RGBA')

                # Resize and composite
                bg_width, bg_height = background_image.size
                removed_bg_image.thumbnail((bg_width, bg_height))
                
                paste_x = (bg_width - removed_bg_image.width) // 2
                paste_y = (bg_height - removed_bg_image.height) // 2

                composite = background_image.copy()
                composite.paste(removed_bg_image, (paste_x, paste_y), removed_bg_image)

                # Save result
                output_bio = io.BytesIO()
                composite.save(output_bio, format='PNG')
                output_bio.seek(0)
                
                # Send result
                await update.message.reply_photo(
                    photo=output_bio,
                    caption="🎉 Here's your merged selfie!",
                    filename='night_selfie.png'
                )
                
            except Exception as e:
                logger.error(f"Error processing images: {e}")
                await update.message.reply_text("❌ Sorry, I ran out of memory. Try again in a minute!")
            
            finally:
                # Clean up
                if user_id in user_data:
                    del user_data[user_id]
                    
    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await update.message.reply_text("❌ Sorry, something went wrong! Try sending the photos again.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by Updates."""
    logger.error(f"Update {update} caused error {context.error}")

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Start the Bot
    logger.info("Bot is starting...")
    
    # Use polling for testing (comment out the next line and uncomment webhook section when ready)
    application.run_polling()
    
    # Uncomment below for webhook deployment (and comment out run_polling() above)
    """
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get('PORT', 8443)),
        webhook_url=f"https://pweshy-stuff-ba7d1a1bd9f5.herokuapp.com/{TOKEN}",
        url_path=TOKEN,
        drop_pending_updates=True
    )
    """

if __name__ == '__main__':
    main()