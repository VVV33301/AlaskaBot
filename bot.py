import discord
from discord import app_commands
import asyncio
import json
import sqlalchemy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
import youtube_dl
from pymorphy2 import MorphAnalyzer
from re import sub
from transliterate import translit
from googletrans import Translator
from random import randint
from os import remove, walk, path, listdir, getcwd
from httpcore._exceptions import ReadTimeout

from settings import TOKEN

morph = MorphAnalyzer()
translator = Translator()


def find_ffmpeg():
    for dirpath, dirname, filename in walk('/'):
        if 'ffmpeg.exe' in filename:
            return path.join(dirpath, 'ffmpeg.exe')


def delete_yt():
    for file in listdir(getcwd()):
        if file.startswith('youtube'):
            remove(file)


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
    async with session() as s:
        g = await s.execute(select(GuildSettings).where(GuildSettings.guild_id == message.guild.id))
        settings = g.scalars().one()
    await message.channel.send(settings.on_bad_word_text.format(member=message.author.mention, server=message.guild))
    print('deleted', message.guild.id, message.author.id)


async def check(message):
    msg_words = [simplify_word(word) for word in sub('[^A-Za-zА-Яа-яёЁ]+', ' ', message.content).split()]
    for word in msg_words:
        word_r = translit(word, 'ru')
        if word in ban_words or word_r in ban_words:
            await ban_message(message)
            return
        for form in morph.normal_forms(word_r):
            if form in ban_words:
                await ban_message(message)
                return
        word_re = word_r.replace('ё', 'е')
        if 'ё' in word_r:
            for form in morph.normal_forms(word_re):
                if form in ban_words:
                    await ban_message(message)
                    return
        for root in ban_roots:
            if root in word or root in word_re or root in word:
                await ban_message(message)
                return
        try:
            if translator.translate(word, 'ru').text in ban_words:
                await ban_message(message)
                return
        except ReadTimeout:
            pass
        print(morph.normal_forms(word), translator.translate(word, 'ru').text, word)


async def create_conn():
    async with sql_engine.begin() as conn:
        await conn.run_sync(SqlAlchemyBase.metadata.create_all)


SqlAlchemyBase = declarative_base()
sql_engine = create_async_engine('sqlite+aiosqlite:///guilds_settings.db')
asyncio.run(create_conn())
session = async_sessionmaker(bind=sql_engine)


class GuildSettings(SqlAlchemyBase):
    __tablename__ = 'settings'

    guild_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    moderation = sqlalchemy.Column(sqlalchemy.Boolean)
    on_bad_word_text = sqlalchemy.Column(sqlalchemy.String)
    on_member_join_text = sqlalchemy.Column(sqlalchemy.String)
    on_member_remove_text = sqlalchemy.Column(sqlalchemy.String)
    call_to_server_text = sqlalchemy.Column(sqlalchemy.String)
    role = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)


youtube_dl.utils.bug_reports_message = lambda: ''
ytdl_format_options = {'format': 'bestaudio/best', 'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
                       'restrictfilenames': True, 'noplaylist': True, 'nocheckcertificate': True,
                       'ignoreerrors': False, 'logtostderr': False, 'quiet': True, 'no_warnings': True,
                       'default_search': 'auto', 'source_address': '0.0.0.0'}
ffmpeg_options = {'options': '-vn'}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.image = data.get("thumbnails")[0]["url"]

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        info = ytdl.extract_info(url, download=not stream)
        data = await loop.run_in_executor(None, lambda: info)
        if 'entries' in data:
            data = data['url'] if stream else data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, executable=find_ffmpeg(),
                                          **ffmpeg_options), data=data), info


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
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    await tree.sync()
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('-----\nGuilds:')
    c = 0
    async with session() as s:
        g = await s.execute(select(GuildSettings))
        guild_list = [i.guild_id for i in g.scalars().all()]
    for n, guild in enumerate(client.guilds, 1):
        c += guild.member_count - 1 if guild.member_count else 0
        print(f'{n}. {guild.id} - "{guild.name}"')
        if guild.id not in guild_list:
            db_sess = session()
            ng = GuildSettings(guild_id=guild.id,
                               moderation=False,
                               on_bad_word_text='Пользователь {member} написал запрещенное слово',
                               on_member_join_text='Привет {member}, добро пожаловать на сервер "{server}"!',
                               on_member_remove_text='Пользователь {member} покинул сервер "{server}"',
                               call_to_server_text='Пользователь {member} зовет Вас на сервер "{server}"!',
                               role=None)
            db_sess.add(ng)
            await db_sess.commit()
    print('Total users in guilds:', c)
    print('-----')


@client.event
async def on_guild_join(guild):
    if guild.system_channel is not None:
        await guild.system_channel.send('Привет! Меня зовут AlaskaBot и я ваш новый бот!')
        ng = GuildSettings(guild_id=guild.id,
                           moderation=False,
                           on_bad_word_text='Пользователь {member} написал запрещенное слово',
                           on_member_join_text='Привет {member}, добро пожаловать на сервер "{server}"!',
                           on_member_remove_text='Пользователь {member} покинул сервер "{server}"',
                           call_to_server_text='Пользователь {member} зовет Вас на сервер "{server}"!',
                           role=None)
        db_sess = session()
        db_sess.add(ng)
        await db_sess.commit()
        print('new guild', guild.id)


@client.event
async def on_member_join(member):
    guild = member.guild
    async with session() as s:
        g = await s.execute(select(GuildSettings).where(GuildSettings.guild_id == member.guild.id))
        settings = g.scalars().one()
    if settings.role:
        await member.add_roles(guild.get_role(settings.role))
    if guild.system_channel is not None:
        await guild.system_channel.send(settings.on_member_join_text.format(member=member.mention, server=guild.name))
    print('join', guild.id, member.id)


@client.event
async def on_member_remove(member):
    guild = member.guild
    async with session() as s:
        g = await s.execute(select(GuildSettings).where(GuildSettings.guild_id == member.guild.id))
        settings = g.scalars().one()
    if guild.system_channel is not None and member.id != client.user.id:
        await guild.system_channel.send(settings.on_member_remove_text.format(member=member.mention, server=guild.name))
    print('remove', guild.id, member.id)


@client.event
async def on_message(message):
    if not message.guild or message.author.id == client.user.id:
        return
    async with session() as s:
        g = await s.execute(select(GuildSettings).where(GuildSettings.guild_id == message.guild.id))
        settings = g.scalars().one()
    if settings.moderation:
        await check(message)


@client.event
async def on_raw_message_edit(payload):
    try:
        message = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if not message.guild or message.author.id == client.user.id:
            return
    except AttributeError:
        return
    async with session() as s:
        g = await s.execute(select(GuildSettings).where(GuildSettings.guild_id == message.guild.id))
        settings = g.scalars().one()
    if settings.moderation:
        await check(message)


@tree.command(name='change_settings', description='Изменить настройки сервера (пользователь={member}, сервер={server})')
@app_commands.guild_only()
@app_commands.describe(on_bad_word_text='Вывод, когда пользователь вводит плохое слово',
                       on_member_join_text='Вывод, когда на сервер заходит новый пользователь',
                       on_member_remove_text='Вывод, когда пользователь покидает сервер',
                       call_to_server_text='Текст вызова пользователя на сервер',
                       default_role='Роль по умолчанию (указать роль либо её id)')
async def change_settings(interaction, on_bad_word_text: str = None, on_member_join_text: str = None,
                          on_member_remove_text: str = None, call_to_server_text: str = None,
                          default_role: discord.Role = None):
    if interaction.user.guild_permissions.administrator:
        sess = session()
        async with session() as s:
            g = await s.execute(select(GuildSettings).where(GuildSettings.guild_id == interaction.guild.id))
            settings = g.scalars().one()
        if on_bad_word_text:
            settings.on_bad_word_text = on_bad_word_text
        if on_member_join_text:
            settings.on_member_join_text = on_member_join_text
        if on_member_remove_text:
            settings.on_member_remove_text = on_member_remove_text
        if call_to_server_text:
            settings.call_to_server_text = call_to_server_text
        if default_role:
            settings.role = default_role.id
        await sess.commit()
        await interaction.response.send_message('Настройки бота для сервера изменены!')
        print('change_settings', interaction.guild_id, interaction.user.id)


@tree.command(name='moderation', description='Включить/отключить удаление нежелательных сообщений')
@app_commands.guild_only()
async def moderation(interaction, value: bool):
    if interaction.user.guild_permissions.administrator:
        sess = session()
        async with session() as s:
            g = await s.execute(select(GuildSettings).where(GuildSettings.guild_id == interaction.guild.id))
            settings = g.scalars().one()
        settings.moderation = value
        await sess.commit()
        await interaction.response.send_message(f'Модерация {"включена" if value else "отключена"}')
        print('moderation', interaction.guild_id, interaction.user.id, value)
    else:
        await interaction.response.send_message('Необходимо обладать правами администратора')


@tree.command(name='random_integer', description='Вывести случайное число (по умолчанию от 0 до 100)')
@app_commands.describe(minimal='Минимальное число', maximal='Максимальное число')
async def random_integer(interaction, minimal: int = 0, maximal: int = 100):
    if minimal <= maximal:
        await interaction.response.send_message(randint(minimal, maximal))
    else:
        await interaction.response.send_message('Ошибка: число *minimal* больше числа *maximal*')
    try:
        print('random', interaction.guild_id, interaction.user.id)
    except AttributeError:
        print('random', None, interaction.user.id)


@tree.command(name='generate_spam', description='Начать спам')
@app_commands.guild_only()
@app_commands.describe(count='Количество сообщений (не более 100)', text='Текст сообщений')
async def generate_spam(interaction, count: int = 1, text: str = 'спамить'):
    count = 100 if count > 100 else count
    global spam_flag
    spam_flag = True
    await interaction.response.send_message(text)
    for _ in range(1, count):
        if spam_flag:
            await interaction.channel.send(text)
        else:
            break
    print('generate_spam', interaction.guild_id, interaction.user.id)


@tree.command(name='stop_spam', description='Остановить спам')
@app_commands.guild_only()
async def stop_spam(interaction):
    global spam_flag
    spam_flag = False
    await interaction.response.send_message('Остановка...')
    print('stop_spam', interaction.guild_id, interaction.user.id)


@tree.command(name='call_to_server', description='Позвать пользователя')
@app_commands.guild_only()
@app_commands.describe(member='Пользователь')
async def call_to_server(interaction, member: discord.User):
    try:
        await interaction.response.send_message(f'Вызов {member.mention}')
        if member.id == client.user.id:
            await interaction.channel.send('Я уже с вами!')
        elif member.id == interaction.user.id:
            await member.send('Зачем кому-то приглашать самого себя?')
        else:
            async with session() as s:
                g = await s.execute(select(GuildSettings).where(GuildSettings.guild_id == interaction.guild.id))
                settings = g.scalars().one()
            await member.send(settings.call_to_server_text.format(member=interaction.user, server=interaction.guild))
        print('call_to_server', interaction.guild_id, interaction.user.id, member.id)
    except discord.Forbidden:
        await interaction.response.send_message(f'Невозможно вызвать {member.mention}')
        print('call_to_server failed', interaction.guild_id, interaction.user.id, member.id)


@tree.command(name='play_music', description='Запустить музыку из ютуба')
@app_commands.guild_only()
@app_commands.describe(yt_url='Полная ссылка на видео из ютуба',
                       channel='Голосовой канал для воспроизведения музыки (по умолчанию тот, на котором вы)',
                       stream='Скачивать видео заранее (медленнее) или во время воспроизведения (опаснее)')
async def play_music(interaction, yt_url: str = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                     channel: discord.VoiceChannel = None, stream: bool = False):
    if not channel:
        try:
            channel = interaction.user.voice.channel
        except AttributeError:
            await interaction.response.send_message('Вы не указали голосовой канал!')
            return
    await interaction.response.defer()
    music, info = await YTDLSource.from_url(yt_url, loop=client.loop, stream=stream)
    text = f'**Воспроизводится:** `{info["title"]}`'
    await interaction.followup.send(content=text)
    try:
        await channel.connect()
        print('music_play', interaction.guild_id, interaction.user.id, channel.id)
        voice_client = interaction.guild.voice_client
        if voice_client.is_connected():
            voice_client.play(music)
        while voice_client.is_playing():
            await asyncio.sleep(1)
        await voice_client.disconnect()
    except Exception as e:
        await interaction.response.edit_message(content='Ошибка воспроизведения')
        print('music_error', e.__class__.__name__, e)
    delete_yt()


@tree.command(name='stop_music', description='Остановить музыку')
@app_commands.guild_only()
async def stop_music(interaction):
    voice_client = interaction.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
        await interaction.response.send_message('Музыка остановлена')
        print('stop_music', interaction.guild_id, interaction.user.id)
        delete_yt()
    else:
        await interaction.response.send_message('Ошибка: Сейчас ночего не воспроизводится')


@tree.command(name='help', description='Показать описания команд')
async def bot_help(interaction):
    text = ['**AlaskaBot**', '*Это бот, имеющий набор ничем не связанных команд, но необходимых каждому пользователю*',
            'Описание команд:']
    for c in sorted(tree.get_commands(), key=lambda x: x.name):
        text.append(f'> **{c.name}** - *{c.description}*{" (работает только на серверах)" if c.guild_only else ""}')
    await interaction.response.send_message('\n'.join(text))
    print('help', interaction.user.id)


if __name__ == '__main__':
    client.run(TOKEN)
