import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from database.database import add_user, del_user, full_userbase, present_user

from config import (
    ADMINS,
    FORCE_MSG,
    START_MSG,
    FORCE_SUB_CHANNEL,
    FORCE_SUB_CHANNEL2,
    DISABLE_CHANNEL_BUTTON,
    PROTECT_CONTENT,
    CUSTOM_CAPTION,
)

# Function to check if the user is subscribed
async def is_subscribed(client: Client, user_id: int) -> bool:
    try:
        for channel in [FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2]:
            member = await client.get_chat_member(channel, user_id)
            if member.status not in ("member", "administrator", "creator"):
                return False
        return True
    except Exception:
        return False


@Client.on_message(filters.command('start') & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id

    # Check if user is subscribed
    if not await is_subscribed(client, user_id):
        buttons = [
            [
                InlineKeyboardButton("Join Channel 1", url=f"https://t.me/{FORCE_SUB_CHANNEL}"),
                InlineKeyboardButton("Join Channel 2", url=f"https://t.me/{FORCE_SUB_CHANNEL2}"),
            ],
            [
                InlineKeyboardButton("Try Again", url=f"https://t.me/{client.username}?start=start"),
            ],
        ]
        await message.reply(
            text=FORCE_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id,
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True,
            quote=True,
        )
        return

    # Add the user to the database if not already added
    if not await present_user(user_id):
        try:
            await add_user(user_id)
        except Exception as e:
            logging.error(f"Error adding user to database: {e}")

    # Welcome message for subscribed users
    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("About Me", callback_data="about"),
                InlineKeyboardButton("Close", callback_data="close"),
            ]
        ]
    )
    await message.reply(
        text=START_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=None if not message.from_user.username else '@' + message.from_user.username,
            mention=message.from_user.mention,
            id=message.from_user.id,
        ),
        reply_markup=reply_markup,
        disable_web_page_preview=True,
        quote=True,
    )


@Client.on_message(filters.command('users') & filters.private & filters.user(ADMINS))
async def get_users(client: Client, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text="<b>Processing...</b>")
    users = await full_userbase()
    await msg.edit(f"<b>Total Users:</b> {len(users)}")


@Client.on_message(filters.command('broadcast') & filters.private & filters.user(ADMINS))
async def broadcast_message(client: Client, message: Message):
    if message.reply_to_message:
        all_users = await full_userbase()
        broadcast_msg = message.reply_to_message
        total = 0
        successful = 0
        blocked = 0
        deleted = 0
        unsuccessful = 0

        pls_wait = await message.reply("<i>Broadcasting message. This might take some time...</i>")
        for user_id in all_users:
            try:
                await broadcast_msg.copy(user_id)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await broadcast_msg.copy(user_id)
                successful += 1
            except UserIsBlocked:
                await del_user(user_id)
                blocked += 1
            except InputUserDeactivated:
                await del_user(user_id)
                deleted += 1
            except Exception as e:
                logging.error(f"Broadcast failed for {user_id}: {e}")
                unsuccessful += 1
            total += 1

        status = f"""
<b>Broadcast Completed</b>
Total Users: <code>{total}</code>
Successful: <code>{successful}</code>
Blocked: <code>{blocked}</code>
Deleted Accounts: <code>{deleted}</code>
Failed: <code>{unsuccessful}</code>
"""
        await pls_wait.edit(status)
    else:
        msg = await message.reply("<i>Please reply to a message to broadcast.</i>")
        await asyncio.sleep(8)
        await msg.delete()

