import os
from dotenv import load_dotenv
import discord
from discord.ext import tasks

TEST_GUILD_ID = 1454779701263597696
TEST_CHANNEL_ID = 1454779702089617513

class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged on as', self.user)

    async def on_message(self, message):
        if message.author != self.user:
            return

        if message.content == 'ping':
            await message.channel.send('pong')

        print([m async for m in message.channel.history(limit=100)])

    async def setup_hook(self) -> None:
        # start the task to run in the background
        self.my_background_task.start()

    @tasks.loop(seconds=60)  # task runs every 60 seconds
    async def my_background_task(self):
        channel = self.get_channel(TEST_CHANNEL_ID)
        await channel.send("test")

    @my_background_task.before_loop
    async def before_my_task(self):
        await self.wait_until_ready()  # wait until the bot logs in

def main():
    load_dotenv()
    token = os.getenv('DISCORD_TOKEN')
    client = MyClient()
    client.run(token)


if __name__ == '__main__':
    main()
