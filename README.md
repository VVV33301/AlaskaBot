<h1 align="center"> 
  <p> AlaskaBot </p>
  <img src="https://user-images.githubusercontent.com/117539159/231544944-244326ad-60f5-42d9-9b4f-db13ffde0158.png" /> 
</h1>

![Python versions](https://img.shields.io/pypi/pyversions/discord.py)
![discord.py version](https://img.shields.io/badge/discord.py-2.2.2-green)

Это Discord бот написанный на языке `Python` при помощи библиотеки `discord.py`.
Используемые библиотеки: *discord.py*, *asyncio*, *sqlalchemy*, *youtube_dl*, *pymorphy2*,
*googletrans*, *json*, *re*, *random*, *os*, *math*, *typing*; 
а также используется программное обеспечение [FFmpeg](https://ffmpeg.org/).

Все библиотеки для установки [здесь](requirements.txt)

## Состав бота

  Бот состоит из следующих файлов:

  + **bot.py** - главный файл бота
  + **buttons.py** - кнопки для create_vote()
  + **translator.py** - перевод с транслита на русский для check()
  + **guilds_settings.db** - база данных для серверов
  + **ban_words.json** *и* **ban_roots.json** - списки нецензурной лексики для check()

  Для работы бота нужно создать файл `settings.py`, в котором необходимо создать переменную `TOKEN`, в которой сохранить свой токен;
  также необходимо иметь на компьютере установленный `ffmpeg.exe` последней версии

### Возможная ошибка в библиотеке youtube_dl

  Если не работает команда `/play_music` для видео с Youtube, то необходимо изменить параметры библиотеки **youtube_dl**: В ***.../youtube_dl/extractor/youtube.py*** в строке 1794 в `self._search_regex(...)` добавить аргумент `fatal=False`
  
## Команды
  
  Функционал бота - *модерация*, *написание спама*, *отправка личных сообщений*, *воспроизведение музыки* и т.д.
  
  + **/help** - Показать описания команд
  + **/information** - Вывести информацию о сервере
    + *bot* - Информация о боте
    + *server* - Информация о сервере
    + *members* - Список участников сервера 
  + **/moderation** - Включить/отключить удаление нежелательных сообщений
  + **/change_settings** - Изменить настройки сервера
    + *on_bad_word_text* - Вывод, когда пользователь вводит плохое слово
    + *on_member_join_text* - Вывод, когда на сервер заходит новый пользователь
    + *on_member_remove_text* - Вывод, когда пользователь покидает сервер
    + *call_to_server_text* - Текст вызова пользователя на сервер
    + *default_role* - Роль по умолчанию
    + *spam_count_max* - Максимальное кол-во сообщений в команде generate_spam
  + **/calculate** - Посчитать математические выражения
  + **/random_integer** - Вывести случайное число (по умолчанию от 0 до 100)
  + **/call_to_server** - Позвать пользователя
  + **/generate_spam** - Начать спам
  + **/stop_spam** - Остановить спам
  + **/play_music** - Запустить музыку из ютуба
  + **/stop_music** - Остановить музыку
  + **/vote** - Создать опрос

## Связь с разработчиками

Официальный сервер бота: [AlaskaBot - сервер](https://discord.gg/X3WjJPAEsV)
