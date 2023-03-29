import discord
import json
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from pymorphy2 import MorphAnalyzer
from re import sub
from transliterate import translit
from random import randint


def simplify_word(word):
    last_letter = ''
    result = ''
    for letter in word:
        if letter != last_letter:
            last_letter = letter
            result += letter
    return result.lower()


async def ban_message(message):
    try:
        await message.delete()
    except Exception as e:
        print('error', e.__class__.__name__)
    settings = session().query(GuildSettings).filter(GuildSettings.guild_id == message.guild.id).first()
    await message.channel.send(settings.on_bad_word_text.format(member=message.author.mention))
    print('deleted', message.guild.id, message.author.id)


async def check(message):
    msg_words = [simplify_word(word) for word in translit(sub('[^A-Za-zА-Яа-яёЁ]+', ' ',
                                                              message.content), 'ru').split()]
    for word in msg_words:
        if word in ban_words:
            await ban_message(message)
            return
        for form in morph.normal_forms(word):
            if form in ban_words:
                await ban_message(message)
                return
        word_ = word.replace('ё', 'е')
        if 'ё' in word:
            for form in morph.normal_forms(word_):
                if form in ban_words:
                    await ban_message(message)
                    return
        for root in ban_roots:
            if root in word or root in word_:
                await ban_message(message)
                return


SqlAlchemyBase = declarative_base()
sql_engine = sqlalchemy.create_engine('sqlite:///guilds_settings.db')
SqlAlchemyBase.metadata.create_all(sql_engine)
session = sessionmaker(bind=sql_engine)


class GuildSettings(SqlAlchemyBase):
    __tablename__ = 'settings'

    guild_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    moderation = sqlalchemy.Column(sqlalchemy.Boolean)
    on_bad_word_text = sqlalchemy.Column(sqlalchemy.String)
    on_member_join_text = sqlalchemy.Column(sqlalchemy.String)
    on_member_remove_text = sqlalchemy.Column(sqlalchemy.String)
    call_to_server_text = sqlalchemy.Column(sqlalchemy.String)
    role = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)


morph = MorphAnalyzer()

spam_flag = False
ban_words, ban_roots = [], []
with open('ban_words.json', encoding='utf-8') as words:
    ban_list = json.load(words)
    for w in ban_list:
        ban_words.append(w['word'])
with open('ban_roots.json', encoding='utf-8') as words:
    ban_list = json.load(words)
    for w in ban_list:
        ban_roots.append(w)

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
    for n, guild in enumerate(client.guilds, 1):
        c += guild.member_count - 1 if guild.member_count else 0
        print(f'{n}. {guild.id} - "{guild.name}"')
    print('Total users:', c)
    print('-----')


@client.event
async def on_guild_join(guild):
    if guild.system_channel is not None:
        await guild.system_channel.send('Привет! Меня зовут AlaskaBot и я ваш новый бот!')
        ng = GuildSettings(guild_id=0,
                           moderation=False,
                           on_bad_word_text='Пользователь {member} написал запрещенное слово',
                           on_member_join_text='Привет {member}, добро пожаловать на сервер "{server}"!',
                           on_member_remove_text='Пользователь {member} покинул сервер "{server}"',
                           call_to_server_text='Пользователь {member} зовет Вас на сервер "{server}"!',
                           role=None)
        db_sess = session()
        db_sess.add(ng)
        db_sess.commit()
        print('new server', guild.id)


@client.event
async def on_member_join(member):
    guild = member.guild
    settings = session().query(GuildSettings).filter(GuildSettings.guild_id == member.guild.id).first()
    if settings.role:
        await member.add_roles(guild.get_role(settings.role))
    if guild.system_channel is not None:
        await guild.system_channel.send(settings.on_member_join_text.format(member=member.mention, server=guild.name))
    print('join', guild.id, member.id)


@client.event
async def on_member_remove(member):
    guild = member.guild
    settings = session().query(GuildSettings).filter(GuildSettings.guild_id == member.guild.id).first()
    if guild.system_channel is not None and member.id != client.user.id:
        await guild.system_channel.send(settings.on_member_remove_text.format(member=member.mention, server=guild.name))
    print('remove', guild.id, member.id)


@client.event
async def on_message(message):
    settings = session().query(GuildSettings).filter(GuildSettings.guild_id == message.guild.id).first()
    if settings.moderation:
        await check(message)


@client.event
async def on_raw_message_edit(payload):
    message = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
    settings = session().query(GuildSettings).filter(GuildSettings.guild_id == message.guild.id).first()
    if settings.moderation:
        await check(message)


@tree.command(name='moderation', description='включить/отключить удаление нежелательных сообщений')
async def moderation(interaction, value: bool):
    try:
        sess = session()
        settings = sess.query(GuildSettings).filter(GuildSettings.guild_id == interaction.guild.id).first()
        if interaction.user.guild_permissions.administrator:
            settings.moderation = value
            sess.commit()
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
        settings = session().query(GuildSettings).filter(GuildSettings.guild_id == interaction.guild.id).first()
        await member.send(settings.call_to_server_text.format(member=interaction.user, server=interaction.guild))
    print('call_to_server', interaction.guild_id, interaction.user.id, member.id)


if __name__ == '__main__':
    with open('token') as token:
        client.run(token.readlines()[0])
