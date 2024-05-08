import asyncio
import os
import sys
import time
from pyrogram import Client, idle
from pyrogram.enums import ParseMode, ChatType, ChatMemberStatus
from pyrogram.handlers import MessageHandler, ChatMemberUpdatedHandler
from pyrogram.session.session import Session
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import Database
import redis
# Genera sessione pyro
async def pyro(token):
    Session.notice_displayed = True

    API_HASH = ''
    API_ID = ''

    bot_id = str(token).split(':')[0]
    app = Client(
        'sessioni/session_bot' + str(bot_id),
        api_hash=API_HASH,
        api_id=API_ID,
        bot_token=token,
        workers=20,
        sleep_threshold=30
    )
    return app

async def wrap_send_del(bot: Client, chatid: int, text: str):
    delete=await db.getLastmsg(chatid)
    delete=delete[0]
    if int(delete) != 0:
        try:
            await bot.delete_messages(chatid, int(delete))
        except Exception as e:
            print(str(e))
    try:
        send = await bot.send_message(chatid, text)
        await db.updateLastmsg(send.id, chatid)
    except Exception as e:
        print("EXC in wrap_send_del:", str(e))

def checkPiu(text):
    return all(char == '+' for char in text)

async def chat_handler(bot, update):
    old_member = update.old_chat_member
    new_member = update.new_chat_member
    if old_member and not old_member.user.id == bot_id: return
    if new_member and not new_member.user.id == bot_id: return 
    if update.chat.type == ChatType.CHANNEL:
        try:
            await bot.leave_chat(chat_id=update.chat.id)
        except Exception as e:
            print(str(e))
        return
    if (not update.old_chat_member or update.old_chat_member.status == ChatMemberStatus.BANNED): # controllo se l'evento è specificamente di aggiunta
        members=await bot.get_chat_members_count(update.chat.id)
        if members<50:
            await bot.send_message(update.chat.id, "Mi dispiace, il bot è abilitato solamente per gruppi con almeno 50 utenti, riaggiungilo quando avrai raggiunto quella soglia, per qualsiasi chiarimento @spidernukleo")
            await bot.leave_chat(chat_id=update.chat.id)
        elif update.chat.type == ChatType.GROUP:
            await bot.send_message(update.chat.id, "Mi dispiace, il bot è abilitato solamente per SUPERGRUPPI, riaggiungilo quando avrai reso questo gruppo un supergruppo, per qualsiasi chiarimento @spidernukleo")
            await bot.leave_chat(chat_id=update.chat.id)
        else:
            await bot.send_message(update.chat.id, "Grazie per aver aggiunto Reputation Bot!\nDa ora potrete rispondere ai messaggi che ritenete meritevoli con dei + (fino a un massimo di 10) e aumenterà la reputazione di quell'utente!\n\nCol comando /top potrete vedere la classifica delle top reputazioni\nPer qualsiasi problema @spidernukleo")
            await db.addids(update.chat.id)
            await bot.send_message("spidernukleo", f"✅ Nuova aggiunta gruppo: {update.chat.title}\nAggiunto da: <a href='tg://user?id={update.from_user.id}'>{update.from_user.first_name}</a>")
            
    return

async def bot_handler(bot, message):
    tipo = message.chat.type
    if message.media or message.service: return
    text = str(message.text)
    if text == '/start' or text == '/start@ReputationCountBot':
        chatid = message.chat.id
        if tipo==ChatType.PRIVATE:
            text="Con questo bot puoi introdurre i tuoi gruppi al concetto di Reputazione, quando un utente manda un messaggio che ti piace o del content veramente figo, puoi rispondergli con dei + e vedrai la sua statistica di Reputazione salire del numero di + con cui gli hai risposto!\n\nPuoi vedere la leaderboard top Reputazione del gruppo con /top\nPremi il bottone qua sotto per aggiungere il bot ai tuoi gruppi ora!\n\nCreato da @spidernukleo"
            await bot.send_message(chatid, text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Aggiungi ora Reputation Bot!",url="https://t.me/ReputationCountBot?startgroup")]]))
        else:
            await bot.send_message(chatid, "Grazie per aver aggiunto Reputation Bot!\nDa ora potrete rispondere ai messaggi che ritenete meritevoli con dei + (fino a un massimo di 10) e aumenterà la reputazione di quell'utente!\n\nCol comando /top potrete vedere la classifica delle top reputazioni\nPer qualsiasi problema @spidernukleo")

    elif text == '/top' or text== '/top@ReputationCountBot':
        chatid = message.chat.id
        if tipo==ChatType.PRIVATE:
            await bot.send_message(chatid, "Comando disponibile solo nei gruppi!")
        else:
            last_time=redis.get(chatid)
            if last_time:
                elapsed_time = time.time() - float(last_time)
                if elapsed_time<20: return
            redis.set(chatid, time.time())
            top = await db.top10rep(chatid)
            text="<b>CLASSIFICA (record)</b> 🔝:"

            for idx, line in enumerate(top, start=1):
                user = await bot.get_users(line[0])
                medal_emojis = {1: "🥇", 2: "🥈", 3: "🥉", 10: "🔟"}
                position = medal_emojis.get(idx, f"{idx}️⃣")
                text+=f"\n{position} {user.first_name} <code><b>•</b></code> {line[1]}"

            text+="\n\n<i>Per qualsiasi problema @nukleolimitatibot</i>"
            await bot.send_message(chatid, text)
    
    elif text.startswith("+"): #se inizia con +
        if message.reply_to_message is not None: #se è una reply
            if message.reply_to_message.from_user is not None and not message.reply_to_message.from_user.is_bot: #se è una reply non a un bot
                if message.reply_to_message.from_user.id != message.from_user.id: #se è una reply non a se stessi
                    if tipo!=ChatType.PRIVATE: #se è in un gruppo
                        text=text.replace(" ","")
                        if checkPiu(text):
                            userid = message.from_user.id
                            last_time=redis.get(userid)
                            if last_time:
                                elapsed_time = time.time() - float(last_time)
                                if elapsed_time<3: return
                            redis.set(userid, time.time())
                            chatid = message.chat.id
                            aumento = min(text.count('+'), 10)
                            repMandatore=await db.getReputazione(chatid,userid)
                            repRicevitore=await db.getReputazione(chatid, message.reply_to_message.from_user.id)

                            if repMandatore is not None and repRicevitore is not None: #se entrambi esistenti
                                repMandatore=repMandatore[0]
                                repRicevitore=repRicevitore[0]+aumento

                            elif repMandatore is None and repRicevitore is None: #se entrambi nuovi
                                await db.generaNuoviRep(chatid, userid)
                                await db.generaNuoviRep(chatid, message.reply_to_message.from_user.id)
                                repMandatore=0
                                repRicevitore=aumento

                            elif repMandatore is None and repRicevitore is not None: #se + nuovo e ricevente esiste
                                await db.generaNuoviRep(chatid, userid)
                                repMandatore=0
                                repRicevitore=repRicevitore[0]+aumento

                            elif repMandatore is not None and repRicevitore is None: #se + esistente e ricenvete nuovo
                                await db.generaNuoviRep(chatid, message.reply_to_message.from_user.id)
                                repMandatore=repMandatore[0]
                                repRicevitore=aumento

                            await db.updateReputazione(repRicevitore, chatid, message.reply_to_message.from_user.id)
                            await wrap_send_del(bot, chatid, f"<b>{message.from_user.first_name}</b> ({repMandatore}) ha alzato la Reputazione di <b>{message.reply_to_message.from_user.first_name}</b> ({repRicevitore})")
    return


async def main(bot_id):
    print(f'Genero sessione [{bot_id}] > ', end='')
    SESSION = await pyro(token=TOKEN)
    HANDLERS = {
        'msg': MessageHandler(bot_handler),
        'chat': ChatMemberUpdatedHandler(chat_handler)
    }
    SESSION.add_handler(HANDLERS['msg'])
    SESSION.add_handler(HANDLERS['chat'])


    print('avvio > ', end='')
    await SESSION.start()

    print('avviati!')
    await idle()

    print('Stopping > ', end='')
    await SESSION.stop()

    await db.close()
    loop.stop()
    print('stopped!\n')
    exit()


if __name__ == '__main__':
    TOKEN = ''
    bot_id = int(TOKEN.split(':')[0])
    loop = asyncio.get_event_loop()
    db = Database(loop=loop)
    redis = redis.Redis(host='localhost', port=6379, db=0)
    loop.run_until_complete(main(bot_id))
    exit()
