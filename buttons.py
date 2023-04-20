import discord

class VoteView(discord.ui.View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.users_list: list = []


class VoteButton(discord.ui.Button):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback: discord.ui.Button.callback = self.callback

    async def callback(self, interaction: discord.Interaction):
        try:
            if interaction.user.id not in self.view.users_list:
                self.label: discord.ui.Button.label = str(int(self.label) + 1)
                self.view.users_list.append(interaction.user.id)
            await interaction.response.edit_message(view=self.view)
        except Exception:
            pass
