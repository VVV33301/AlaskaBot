import discord

class VoteView(discord.ui.View):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.users_list = [bot.user.id]


class VoteButton(discord.ui.Button):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback = self.callback

    async def callback(self, interaction):
        try:
            if interaction.user.id not in self.view.users_list:
                self.label = str(int(self.label) + 1)
                self.view.users_list.append(interaction.user.id)
                await interaction.response.edit_message(view=self.view)
                print('button click', interaction.user.id)
        except Exception:
            print('button error', interaction.user.id)
