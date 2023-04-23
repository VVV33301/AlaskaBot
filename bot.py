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
from re import sub, search
from googletrans import Translator
from random import randint
from os import walk, path, getcwd
import math
from typing import Union, Literal
# Импорт библиотек

from settings import TOKEN
from translator import translate
from buttons import VoteButton, VoteView
# Импорт дополнительных файлов бота

morph = MorphAnalyzer()  # Класс для анализа слов
translator = Translator()  # Переводчик
calc_list = ['int', 'float', 'sum', 'round', *dir(math)[5:], 'True', 'False', 'and', 'or', 'not']  # Список разрешенных функций для калькулятора


def find_ffmpeg() -> str:
    """Найти приложение ffmpeg"""
    for dirpath, dirname, filename in walk(getcwd()):  # Поиск в локальном окружении
        if 'ffmpeg.exe' in filename:
            print('ffmpeg.exe found in', dirpath)
            return path.join(dirpath, 'ffmpeg.exe')
    for dirpath, dirname, filename in walk('/'):  # Поиск по всему компьютеру
        if 'ffmpeg.exe' in filename:
            print('ffmpeg.exe found in', dirpath)
            return path.join(dirpath, 'ffmpeg.exe')


def simplify_word(word: str) -> str:
    """Ликвидация повторяющихся букв из слова"""
    last_letter = ''
    result = ''
    for letter in word:
        if letter != last_letter:
            last_letter = letter
            result += letter
    return result


async def ban_message(message: discord.Message) -> None:
    """Забанить сообщение и удалить его"""
    try:
        await message.delete()
    except Exception as e:
        print('error', e.__class__.__name__)
    async with session() as s:
        g = await s.execute(select(GuildSettings).where(GuildSettings.guild_id == message.guild.id))
        settings = g.scalars().one()
    await message.channel.send(settings.on_bad_word_text.format(member=message.author.mention, server=message.guild))
    print('deleted', message.guild.id, message.author.id)


async def check(message: str) -> bool:
    """Проверка сообщений на наличие нецензурных слов"""
    msg_words = [word.lower() for word in sub('[^A-Za-zА-Яа-яёЁ]+', ' ', message).split()]
    for word in msg_words:
        word_r = translate(word)
        word_re = word_r.replace('ё', 'е')
        if word in ban_words or word_r in ban_words:  # Проверка слова без изменений
            return True
        for root in ban_roots:  # Проверка корня слова
            if root in word or root in word_re:
                return True
        word = simplify_word(word)
        word_r = translate(word)
        if word in ban_words or word_r in ban_words:  # Проверка измененного слова
            return True
        for form in morph.normal_forms(word_r):  # Проверка слова с морфологическим анализом
            if form in ban_words:
                return True
        word_re = word_r.replace('ё', 'е')
        if 'ё' in word_r:  # Проверка на букву "ё"
            for form in morph.normal_forms(word_re):
                if form in ban_words:
                    return True
        for root in ban_roots:
            if root in word or root in word_re:
                return True
        try:  # Проверка с переводом (все предыдущие проверки)
            if not search('[а-яА-Я]', word):
                word_t = translator.translate(word, 'ru').text
                print('translated')
                if word_t in ban_words:
                    return True
                for form in morph.normal_forms(word_t):
                    if form in ban_words:
                        return True
                word_rt = word_r.replace('ё', 'е')
                if 'ё' in word_r:
                    for form in morph.normal_forms(word_rt):
                        if form in ban_words:
                            return True
                for root in ban_roots:
                    if root in word_t or root in word_rt:
                        return True
            else:
                word_t = word
        except Exception as e:
            print('translate_error', e.__class__.__name__)  # Вывод сообщения об ошибке перевода
            word_t = word
        print(morph.normal_forms(word_t), morph.normal_forms(word_r), word_t, word_r, word)  # Вывод результата обработки (если все проверки были пройдены)


async def create_conn() -> None:
    """Подключение к базе данных"""
    async with sql_engine.begin() as conn:
        await conn.run_sync(SqlAlchemyBase.metadata.create_all)


SqlAlchemyBase = declarative_base()  # Создать локальную базу данных
sql_engine = create_async_engine('sqlite+aiosqlite:///guilds_settings.db')  # Создание движка базы данных
asyncio.run(create_conn())  # Подключение движка
session = async_sessionmaker(bind=sql_engine)  # Генератор сессий


class GuildSettings(SqlAlchemyBase):
    """Столбец базы данных"""
    __tablename__ = 'settings'

    guild_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    moderation = sqlalchemy.Column(sqlalchemy.Boolean)
    spam_count_max = sqlalchemy.Column(sqlalchemy.Integer)
    on_bad_word_text = sqlalchemy.Column(sqlalchemy.String)
    on_member_join_text = sqlalchemy.Column(sqlalchemy.String)
    on_member_remove_text = sqlalchemy.Column(sqlalchemy.String)
    call_to_server_text = sqlalchemy.Column(sqlalchemy.String)
    role = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)


# Настройки для Youtube_dl и ffmpeg
youtube_dl.utils.bug_reports_message = lambda: ''
ytdl_format_options = {'format': 'bestaudio/best', 'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
                       'restrictfilenames': True, 'noplaylist': True, 'nocheckcertificate': True,
                       'ignoreerrors': False, 'logtostderr': False, 'quiet': True, 'no_warnings': True,
                       'default_search': 'auto', 'source_address': '0.0.0.0'}
ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

spam_flag = False  # Разрешение на спам
ban_words, ban_roots = [], []  # Списки с запрещенными корнями и словами
with open('ban_words.json', encoding='utf-8') as words:  # Импорт запрещенных слов
    ban_list = json.load(words)
    for w in ban_list:
        ban_words.append(w['word'])
with open('ban_roots.json', encoding='utf-8') as words:  # Импорт запрещенных корней
    ban_list = json.load(words)
    for w in ban_list:
        ban_roots.append(w)

intents = discord.Intents.default()  # Интенты
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)  # Клиент бота
tree = app_commands.CommandTree(client)  # Командное дерево


@client.event
async def on_ready():
    """Функция, вызываемая при запуске бота"""
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
                               spam_count_max=100,
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
    """Функция, вызываемая при присоединении бота к новому серверу"""
    if guild.system_channel is not None:
        await guild.system_channel.send('Привет! Меня зовут AlaskaBot и я ваш новый бот! Попробуйте команду */help*')
        ng = GuildSettings(guild_id=guild.id,
                           moderation=False,
                           spam_count_max=100,
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
    """Функция, вызываемая при присоединении нового человека к серверу"""
    guild = member.guild
    async with session() as s:
        g = await s.execute(select(GuildSettings).where(GuildSettings.guild_id == member.guild.id))
        settings = g.scalars().one()
        if settings.role:
            await member.add_roles(guild.get_role(settings.role))
        if guild.system_channel is not None:
            await guild.system_channel.send(settings.on_member_join_text.format(
                member=member.mention, server=guild.name))
    print('join', guild.id, member.id)


@client.event
async def on_member_remove(member):
    """Функция, вызываемая при уходе человека из сервера"""
    guild = member.guild
    async with session() as s:
        g = await s.execute(select(GuildSettings).where(GuildSettings.guild_id == member.guild.id))
        settings = g.scalars().one()
        if guild.system_channel is not None and member.id != client.user.id:
            await guild.system_channel.send(settings.on_member_remove_text.format(
                member=member.mention, server=guild.name))
    print('remove', guild.id, member.id)


@client.event
async def on_message(message):
    """Функция, вызываемая при отправке сообщения"""
    if not message.guild or message.author.id == client.user.id:
        return
    async with session() as s:
        g = await s.execute(select(GuildSettings).where(GuildSettings.guild_id == message.guild.id))
        settings = g.scalars().one()
    if settings.moderation:
        if await check(message.content):
            await ban_message(message)


@client.event
async def on_raw_message_edit(payload):
    """Функция, вызываемая при редактировании сообщения"""
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
        if await check(message.content):
            await ban_message(message)


@tree.command(name='help', description='Показать описания команд')
async def bot_help(interaction):
    """Команда Помощь"""
    text = ['**AlaskaBot**', '*Это бот, имеющий набор ничем не связанных команд, но необходимых каждому пользователю*',
            'Функционал - *модерация*, *написание спама*, *отправка личных сообщений*, *воспроизведение музыки* и т.д.',
            'Описание команд:']
    if interaction.guild:
        for c in sorted(tree.get_commands(), key=lambda x: x.name):
            text.append(f'> **{c.name}** - *{c.description}*')
    else:
        for c in sorted(tree.get_commands(), key=lambda x: x.name):
            if not c.guild_only:
                text.append(f'> **{c.name}** - *{c.description}*')
        text.append('*Попробуйте воспользоваться ботом на сервере - больше возможностей!*')
    await interaction.response.send_message('\n'.join(text))
    print('help', interaction.user.id)


@tree.command(name='information', description='Вывести информацию о сервере')
@app_commands.guild_only()
@app_commands.describe(parameter='тип необходимой информации')
async def information(interaction,
                      parameter: Literal['сервер', 'участники', 'бот', 'условия использования', 'значок сервера']):
    """Команда Информация"""
    guild = interaction.guild
    if parameter == 'участники':
        await interaction.response.send_message('\n'.join([f'{n}. {i}' for n, i in
                                                           enumerate(sorted(map(str, guild.members)), 1)]))
    elif parameter == 'сервер':
        await interaction.response.send_message(
            f'Сервер "{guild.name}"\nid: {guild.id}\nУчастников: {guild.member_count}')
    elif parameter == 'бот':
        await interaction.response.send_message(
            f'*AlaskaBot*\nСерверов: {len(t := client.guilds)}\nПользователей: {sum([len(i.members) - 1 for i in t])}')
    elif parameter == 'условия использования':
        await interaction.response.send_message(
            '**Условия использования AlaskaBot**\nAlaskaBot собирает информацию (ID и названия серверов, ID, аватары и '
            'ники пользователей, роли серверов, а также все сообщения) для обработки. ID и роли серверов сохраняются в '
            'базе данных для обработки. Все остальные данные не сохраняются.\nИспользуя AlaskaBot, вы соглашаетесь на '
            'сбор информации')
    elif parameter == 'значок сервера':
        embed = discord.Embed(title=f'Значок сервера *{interaction.guild.name}*', type='image')
        embed.set_image(url=interaction.guild.icon.url)
        await interaction.response.send_message(embed=embed)
    print('information', parameter, interaction.guild_id, interaction.user.id)


@tree.command(name='change_settings', description='Изменить настройки сервера (пользователь={member}, сервер={server})')
@app_commands.guild_only()
@app_commands.describe(on_bad_word_text='Вывод, когда пользователь вводит плохое слово',
                       on_member_join_text='Вывод, когда на сервер заходит новый пользователь',
                       on_member_remove_text='Вывод, когда пользователь покидает сервер',
                       call_to_server_text='Текст вызова пользователя на сервер',
                       default_role='Роль по умолчанию (указать роль либо её id)',
                       spam_count_max='Максимальное кол-во сообщений в команде generate_spam')
async def change_settings(interaction, show_changes: bool = False, on_bad_word_text: str = None,
                          on_member_join_text: str = None, on_member_remove_text: str = None,
                          call_to_server_text: str = None, default_role: discord.Role = None,
                          spam_count_max: int = None):
    """Команда Изменить настройки"""
    if interaction.user.guild_permissions.administrator:
        changes = {}
        async with session() as sess:
            g = await sess.execute(select(GuildSettings).where(GuildSettings.guild_id == interaction.guild.id))
            settings = g.scalars().one()
            if on_bad_word_text:
                settings.on_bad_word_text = on_bad_word_text
                changes['on_bad_word_text'] = on_bad_word_text
            if on_member_join_text:
                settings.on_member_join_text = on_member_join_text
                changes['on_member_join_text'] = on_member_join_text
            if on_member_remove_text:
                settings.on_member_remove_text = on_member_remove_text
                changes['on_member_remove_text'] = on_member_remove_text
            if call_to_server_text:
                settings.call_to_server_text = call_to_server_text
                changes['call_to_server_text'] = call_to_server_text
            if default_role:
                settings.role = default_role.id
                changes['default_role'] = default_role.id
            if spam_count_max:
                settings.spam_count_max = spam_count_max
                changes['spam_count_max'] = spam_count_max
            await sess.commit()
        if show_changes:
            text = '\n'.join(f'{s} изменен на {r}' for s, r in changes.items())
            await interaction.response.send_message(f'Настройки бота для сервера изменены:\n{text}')
        else:
            await interaction.response.send_message('Настройки бота для сервера изменены!')
        print('change_settings', interaction.guild_id, interaction.user.id)


@tree.command(name='moderation', description='Включить/отключить удаление нежелательных сообщений')
@app_commands.guild_only()
async def moderation(interaction, value: bool):
    """Команда Включить модерацию"""
    if interaction.user.guild_permissions.administrator:
        async with session() as sess:
            g = await sess.execute(select(GuildSettings).where(GuildSettings.guild_id == interaction.guild.id))
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
    """Команда Рандомное число"""
    if minimal <= maximal:
        await interaction.response.send_message(randint(minimal, maximal))
    else:
        await interaction.response.send_message('Ошибка: число *minimal* больше числа *maximal*')
    try:
        print('random', interaction.guild_id, interaction.user.id)
    except AttributeError:
        print('random', None, interaction.user.id)


@tree.command(name='calculate', description='Посчитать математические выражения')
@app_commands.describe(expression='Выражение (показать все операции - help)')
async def calculate(interaction, expression: str):
    """Команда Калькулятор"""
    await interaction.response.defer()
    if expression == 'help':
        text = ['***Помощь по команде /calculate***', '**Арифметические знаки:**', '> +\tсложение', '> -\tвычитание',
                '> *\tумножение', '> /\tделение', '> //\tцелочисленное деление', '> **\tстепень',
                '> %\tостаток от деления', '> ()\tскобки', '> []\tскобки для списков', '> < >\tбольше или меньше',
                '> ==\tравно', '> !=\tне равно', '> .\tдробная часть', '> ,\tразделение аргументов в функциях',
                'and - логическое "и"', 'or - логическое "или"', 'not - логическое "не"', 'True - правда',
                'False - ложь', '**Функции:**', 'int() - превращение в целое число',
                'float() - превращение в вещественное число', 'sum() - сложение списка', 'round() - округление',
                '[остальные функции по этой ссылке](<https://docs.python.org/3/library/math.html>)']
        await interaction.followup.send(content='\n'.join(text))
        return
    if expression == 'delete server':
        if interaction.user.guild_permissions.administrator:
            await interaction.followup.send('Удаление сервера...')
            s = morph.parse('секунда')[0]
            for i in range(30):
                await interaction.channel.send(f'До удаления сервера {30 - i} '
                                               f'{s.make_agree_with_number(30 - i).word}')
                await asyncio.sleep(1)
            interaction.channel.send(f'Удаление сервера... ошибка!')
        else:
            await interaction.followup.send('Удаление сервера... у вас недостаточно прав!')
    if "'" in expression or '"' in expression or '@' in expression:
        await interaction.followup.send(content='Ошибка!')
        print('calculate', 'ban', expression)
        return
    for i in sub('[^A-Za-zА-Яа-яёЁ]', ' ', expression).split():
        if not i.isdigit() and i not in calc_list:
            await interaction.followup.send(content='Ошибка!')
            print('calculate', 'ban', expression)
            return
    try:
        res = eval(expression, {"__builtins__": None}, {**math.__dict__, 'int': int, 'float': float,
                                                        'sum': sum, 'round': round})  # Опасно
    except Exception:
        res = None
    try:
        if res is not None:
            text = expression.replace("*", "\*")
            await interaction.followup.send(content=f'{text} = {res}')
        else:
            raise SyntaxError
    except Exception:
        await interaction.followup.send(content='Ошибка!')
        print('calculate', 'error', expression)
        return
    try:
        print('calculate', interaction.guild_id, interaction.user.id)
    except AttributeError:
        print('calculate', None, interaction.user.id)


@tree.command(name='generate_spam', description='Начать спам')
@app_commands.guild_only()
@app_commands.describe(count='Количество сообщений', text='Текст сообщений')
async def generate_spam(interaction, text: str, count: int = 3):
    """Команда Начать спам"""
    if await check(text):
        await interaction.response.send_message('Я не буду этого делать!')
        await asyncio.sleep(1.5)
        await interaction.delete_original_response()
        return
    async with session() as s:
        g = await s.execute(select(GuildSettings).where(GuildSettings.guild_id == interaction.guild.id))
        settings = g.scalars().one()
        if count > (t := settings.spam_count_max):
            count = t
    global spam_flag
    spam_flag = True
    await interaction.response.send_message(text)
    print('generate_spam', interaction.guild_id, interaction.user.id)
    for _ in range(1, count):
        if spam_flag:
            await asyncio.sleep(0.7)
            await interaction.channel.send(text)
        else:
            break


@tree.command(name='stop_spam', description='Остановить спам')
@app_commands.guild_only()
async def stop_spam(interaction):
    """Команда Остановить спам"""
    global spam_flag
    spam_flag = False
    await interaction.response.send_message('Прекращение спама')
    print('stop_spam', interaction.guild_id, interaction.user.id)


@tree.command(name='call_to_server', description='Позвать пользователя')
@app_commands.guild_only()
@app_commands.describe(member='Пользователь')
async def call_to_server(interaction, member: discord.User):
    """Команда Позвать человека"""
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
    except Exception:
        await interaction.response.send_message(f'Невозможно вызвать {member.mention}')
        print('call_to_server failed', interaction.guild_id, interaction.user.id, member.id)


@tree.command(name='play_music', description='Запустить музыку из ютуба')
@app_commands.guild_only()
@app_commands.describe(url='Полная ссылка на видео из ютуба',
                       channel='Голосовой канал для воспроизведения музыки (по умолчанию тот, на котором вы)')
async def play_music(interaction, url: str = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                     channel: discord.VoiceChannel = None):
    """Команда Включить музыку"""
    if interaction.guild.voice_client:
        await interaction.response.send_message('Сначала необходимо остановить музыку, играющую сейчас')
        return
    if not channel:
        try:
            channel = interaction.user.voice.channel
        except AttributeError:
            await interaction.response.send_message('Вы не указали голосовой канал!')
            return
    await interaction.response.defer()
    try:
        with youtube_dl.YoutubeDL(ytdl_format_options) as ydl:
            info = ydl.extract_info(url, download=False)
            iurl = info['formats'][0]['url']
            source = await discord.FFmpegOpusAudio.from_probe(iurl, **ffmpeg_options, executable=find_ffmpeg())
        text = f'**Воспроизводится:** `{info["title"]}`'
        await channel.connect()
        print('music_play', interaction.guild_id, interaction.user.id, channel.id)
        voice_client = interaction.guild.voice_client
        await interaction.followup.send(content=text)
        if voice_client.is_connected():
            voice_client.play(source)
        while voice_client.is_playing():
            await asyncio.sleep(1)
        await voice_client.disconnect()
    except Exception as e:
        try:
            await interaction.followup.send(content='Ошибка воспроизведения')
        except Exception as ee:
            await interaction.response.send_message(content='Ошибка воспроизведения')
            print(ee.__class__.__name__)
        print('music_error', e.__class__.__name__)


@tree.command(name='stop_music', description='Остановить музыку')
@app_commands.guild_only()
async def stop_music(interaction):
    """Команда Остановить музыку"""
    voice_client = interaction.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
        await interaction.response.send_message('Музыка остановлена')
        print('stop_music', interaction.guild_id, interaction.user.id)
    else:
        await interaction.response.send_message('Ошибка: Сейчас ничего не воспроизводится')


@tree.command(name='vote', description='Создать опрос')
@app_commands.guild_only()
@app_commands.describe(question='Вопрос', title='Заголовок (по умолчанию "Опрос")',
                       answers='Варианты ответа в виде эмодзи (разделитель: "|") (по умолчанию ✅|❎)',
                       timeout='Время, после которого опрос закрывается (в секундах)',
                       call_everyone='Вызывать ли всех участников сервера командой @everyone (не рекомендуется)')
async def create_vote(interaction, question: str, title: str = 'Опрос', answers: str = '✅|❎',
                      timeout: float = None, call_everyone: bool = False):
    """Команда Создать опрос"""
    if await check(question) or await check(title):
        await interaction.response.send_message('Я не буду этого делать!')
        await asyncio.sleep(1.5)
        await interaction.delete_original_response()
        return
    text = discord.Embed(title=title, description=question, colour=discord.Colour.blue())
    view = VoteView(timeout=None)
    for n, ans in enumerate(answers.replace(' ', '').split('|')):
        try:
            btn = VoteButton(emoji=ans, label='0')
            view.add_item(btn)
        except Exception:
            await interaction.response.send_message(content='Ошибка составления опроса')
            return
    if call_everyone:
        try:
            await interaction.channel.send('@everyone')
        except Exception:
            await interaction.channel.send('Не получилось позвать всех при помощи everyone')
    print('create_vote', interaction.guild_id, interaction.user.id)
    await interaction.response.send_message(embed=text, view=view)
    if timeout is not None and timeout > 0:
        await asyncio.sleep(timeout)
        for i in filter(lambda x: type(x) == VoteButton, view.children):
            i.disabled = True
        await interaction.edit_original_response(view=view)


@tree.command(name='download_avatar', description='Скачать аватар пользователя')
async def download_avatar(interaction, user: Union[discord.Member, discord.User] = None):
    """Команда Скачать аватар"""
    if not user:
        user = interaction.user
    avatar = user.avatar
    if user.__class__ == discord.Member and user.nick:
        user = user.nick
    if not avatar:
        await interaction.response.send_message(f'У пользователя **{user}** нет аватара')
    else:
        embed = discord.Embed(title=f'Аватар пользователя {user}', type='image')
        embed.set_image(url=avatar)
        await interaction.response.send_message(embed=embed)


if __name__ == '__main__':  # Запуск бота
    client.run(TOKEN)
