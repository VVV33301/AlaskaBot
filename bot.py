import discord

from random import randint

spam_bool = False

on_member_join_text = 'Привет {member}, добро пожаловать на сервер "{server}"!'
on_member_remove_text = 'Пользователь {member} покинул сервер "{server}"'
call_to_server_text = 'Пользователь {user} зовет Вас на сервер "{server}"!'

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


@tree.command(name='random', description='Вывести случайное число (по умолчанию от 0 до 100)')
async def random(interaction, minimal: int = 0, maximal: int = 100):
    if minimal <= maximal:
        await interaction.response.send_message(randint(minimal, maximal))
    else:
        await interaction.response.send_message('Ошибка: число minimal больше числа maximal')
    try:
        print('random', interaction.guild_id, interaction.user.id)
    except AttributeError:
        print('random', None, interaction.user.id)


@tree.command(name='generate_spam', description='Начать спам')
async def generate_spam(interaction, count: int = 1, text: str = 'spam'):
    count = 100 if count > 100 else count
    global spam_bool
    spam_bool = True
    await interaction.response.send_message('start spamming')
    for i in range(count):
        if spam_bool:
            await interaction.channel.send(text)
        else:
            break
    print('generate_spam', interaction.guild_id, interaction.user.id)


@tree.command(name='stop_spam', description='Остановить спам')
async def stop_spam(interaction):
    global spam_bool
    spam_bool = False
    await interaction.response.send_message('Stop spamming')
    print('stop_spam', interaction.guild_id, interaction.user.id)


@tree.command(name='call_to_server', description='Позвать людей')
async def call_to_server(interaction, member: discord.User):
    await interaction.response.send_message(f'Вызов {member.mention}')
    if member.id == client.user.id:
        await interaction.channel.send('Я уже с вами!')
    elif member.id == interaction.user.id:
        await member.send('Зачем кому-то приглашать самого себя?')
    else:
        await member.send(call_to_server_text.format(user=interaction.user, server=interaction.guild))
    print('call_to_server', interaction.guild_id, interaction.user.id, member.id)


if __name__ == '__main__':
    with open('token') as token:
        client.run(token.readlines()[0])
