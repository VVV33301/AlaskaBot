import discord
import json
# import sqlalchemy
# from sqlalchemy.ext.asyncio import create_async_engine
from pymorphy2 import MorphAnalyzer
from re import sub
from transliterate import translit
from random import randint

morph = MorphAnalyzer()
# sql_engine = create_async_engine('sqlite:///guilds_settings.db', echo=True)

moderation_flag = True
on_bad_word_write_text = 'Пользователь {member} написал запрещенное слово'
on_member_join_text = 'Привет {member}, добро пожаловать на сервер "{server}"!'
on_member_remove_text = 'Пользователь {member} покинул сервер "{server}"'
call_to_server_text = 'Пользователь {member} зовет Вас на сервер "{server}"!'

spam_flag = False
ban_words = []
with open('ban_words.json', encoding='ascii') as words:
    ban_list = json.load(words)
    for w in ban_list:
        ban_words.append(w['word'])

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)


@client.event
async def on_ready():
    await tree.sync()
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('-----\nServers:')
    c = 0
    for n, i in enumerate(client.guilds, 1):
        c += i.member_count - 1 if i.member_count else 0
        print(f'{n}. {i.id} - "{i.name}"')
    print('Total users:', c)
    print('-----')


@client.event
async def on_member_join(member):
    guild = member.guild
    if guild.system_channel is not None:
        send = on_member_join_text.format(member=member.mention, server=guild.name)
        await guild.system_channel.send(send)
    print('New user:', member.id)


@client.event
async def on_member_remove(member):
    guild = member.guild
    if guild.system_channel is not None:
        send = on_member_remove_text.format(member=member.mention, server=guild.name)
        await guild.system_channel.send(send)
    print('Removed user:', member.id)


@client.event
async def on_message(message):
    if moderation_flag:
        def simplify_word(word):
            last_letter = ''
            result = ''
            for letter in word:
                if letter != last_letter:
                    last_letter = letter
                    result += letter
            return result.lower()

        msg_words = [simplify_word(word) for word in translit(sub('[^A-Za-zА-Яа-я0-9ёЁ]+', ' ',
                                                                  message.content), 'ru').split()]
        for word in msg_words:
            if word in ban_words:
                try:
                    await message.delete()
                except Exception:
                    pass
                await message.channel.send(on_bad_word_write_text.format(member=message.author.mention))
                print('deleted', message.guild.id, message.author.id)
                return
            for form in morph.normal_forms(word):
                if form in ban_words:
                    try:
                        await message.delete()
                    except Exception:
                        pass
                    await message.channel.send(on_bad_word_write_text.format(member=message.author.mention))
                    print('deleted', message.guild.id, message.author.id)
                    return
            if 'ё' in word:
                for form in morph.normal_forms(word.replace('ё', 'е')):
                    if form in ban_words:
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        await message.channel.send(on_bad_word_write_text.format(member=message.author.mention))
                        print('deleted', message.guild.id, message.author.id)
                        return


@client.event
async def on_raw_message_edit(payload):
    message = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
    if moderation_flag:
        def simplify_word(word):
            last_letter = ''
            result = ''
            for letter in word:
                if letter != last_letter:
                    last_letter = letter
                    result += letter
            return result

        msg_words = [simplify_word(word) for word in translit(sub('[^A-Za-zА-Яа-я0-9ё]+', ' ',
                                                                  message.content), 'ru').split()]
        for word in msg_words:
            if word in ban_words:
                try:
                    await message.delete()
                except Exception:
                    pass
                await message.channel.send(on_bad_word_write_text.format(member=message.author.mention))
                print('deleted_', message.guild.id, message.author.id)
                return
            for form in morph.normal_forms(word):
                if form in ban_words:
                    try:
                        await message.delete()
                    except Exception:
                        pass
                    await message.channel.send(on_bad_word_write_text.format(member=message.author.mention))
                    print('deleted_', message.guild.id, message.author.id)
                    return
            if 'ё' in word:
                for form in morph.normal_forms(word.replace('ё', 'е')):
                    if form in ban_words:
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        await message.channel.send(on_bad_word_write_text.format(member=message.author.mention))
                        print('deleted_', message.guild.id, message.author.id)
                        return


@tree.command(name='moderation', description='включить/отключить удаление нежелательных сообщений')
async def moderation(interaction, value: bool):
    try:
        if interaction.user.guild_permissions.administrator:
            global moderation_flag
            moderation_flag = value
            await interaction.response.send_message(f'Модерация {"включена" if value else "отключена"}')
            print('moderation', value, interaction.guild_id, interaction.user.id)
        else:
            await interaction.response.send_message('Необходимо обладать правами администратора')
    except AttributeError:
        await interaction.response.send_message('Вы не на сервере!')


@tree.command(name='random', description='Вывести случайное число (по умолчанию от 0 до 100)')
async def random(interaction, minimal: int = 0, maximal: int = 100):
    if minimal <= maximal:
        await interaction.response.send_message(randint(minimal, maximal))
    else:
        await interaction.response.send_message('Ошибка: число *minimal* больше числа *maximal*')
    try:
        print('random', interaction.guild_id, interaction.user.id)
    except AttributeError:
        print('random', None, interaction.user.id)


@tree.command(name='generate_spam', description='Начать спам')
async def generate_spam(interaction, count: int = 1, text: str = 'spam'):
    count = 100 if count > 100 else count
    global spam_flag
    spam_flag = True
    await interaction.response.send_message('start spamming')
    for i in range(count):
        if spam_flag:
            await interaction.channel.send(text)
        else:
            break
    print('generate_spam', interaction.guild_id, interaction.user.id)


@tree.command(name='stop_spam', description='Остановить спам')
async def stop_spam(interaction):
    global spam_flag
    spam_flag = False
    await interaction.response.send_message('Stop spamming')
    print('stop_spam', interaction.guild_id, interaction.user.id)


@tree.command(name='call_to_server', description='Позвать пользователя')
async def call_to_server(interaction, member: discord.User):
    await interaction.response.send_message(f'Вызов {member.mention}')
    if member.id == client.user.id:
        await interaction.channel.send('Я уже с вами!')
    elif member.id == interaction.user.id:
        await member.send('Зачем кому-то приглашать самого себя?')
    else:
        await member.send(call_to_server_text.format(member=interaction.user, server=interaction.guild))
    print('call_to_server', interaction.guild_id, interaction.user.id, member.id)


if __name__ == '__main__':
    with open('token') as token:
        client.run(token.readlines()[0])
