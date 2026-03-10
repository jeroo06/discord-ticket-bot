import os
import discord
import discord.interactions

from discord.ext import commands
import datetime
from dotenv import load_dotenv
import io
import asyncio

from scripts.regsetup import description

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='$', intents=intents)

# --- CONFIGURATION ---
CATEGORIAS_TICKETS = {
    "Support": 1480645721672912986,
    "Partner": 1480646025176944752,
    "Highlight": 1480645883346419787
}
ID_CANAL_TRANSCRIPTS = 1479931001089163465

# Lista de IDs de roles que pueden ver los tickets
ROLES_STAFF_IDS = [
    1479548860178108466
    # Puedes añadir más IDs aquí separados por comas
]


# ----------------------------

class BotonCerrar(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, emoji="🔒")
    async def cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Generating transcript and closing channel...", ephemeral=True)

        log_content = f"Transcript for {interaction.channel.name}\n"
        log_content += f"Closed by: {interaction.user} ({interaction.user.id})\n"
        log_content += "-" * 30 + "\n"

        async for message in interaction.channel.history(limit=None, oldest_first=True):
            time = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            log_content += f"[{time}] {message.author}: {message.content}\n"

        canal_logs = bot.get_channel(ID_CANAL_TRANSCRIPTS)
        if canal_logs:
            file = discord.File(io.BytesIO(log_content.encode()), filename=f"transcript-{interaction.channel.name}.txt")
            await canal_logs.send(content=f"Ticket closed: **{interaction.channel.name}**", file=file)

        await asyncio.sleep(3)
        await interaction.channel.delete()


class MenuTickets(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Support", description="General help", emoji="🔨"),
            discord.SelectOption(label="Partner", description="Partner applications", emoji="📢"),
            discord.SelectOption(label="Highlight", description="Request a highlight", emoji="🎥")
        ]
        super().__init__(placeholder="Select a category...", options=options)

    async def callback(self, interaction: discord.Interaction):
        categoria_nombre = self.values[0]
        guild = interaction.guild
        usuario = interaction.user

        id_cat = CATEGORIAS_TICKETS.get(categoria_nombre)
        categoria_discord = guild.get_channel(id_cat)

        # Configuración base de permisos
        permisos = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            usuario: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        # AÑADIR ROLES DE STAFF A LOS PERMISOS
        for rol_id in ROLES_STAFF_IDS:
            rol = guild.get_role(rol_id)
            if rol:
                permisos[rol] = discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                                            read_message_history=True)

        nombre_canal = f"{categoria_nombre}-{usuario.name}".lower().replace(" ", "-")

        nuevo_ticket = await guild.create_text_channel(
            name=nombre_canal,
            category=categoria_discord,
            overwrites=permisos
        )

        await interaction.response.send_message(f"✅ Ticket created: {nuevo_ticket.mention}", ephemeral=True)

        # Mención de todos los roles de staff en el mensaje de bienvenida
        menciones_staff = " ".join([f"<@&{rid}>" for rid in ROLES_STAFF_IDS])

        embed_contenido = discord.Embed(
            description=f"Hello {usuario.mention}, welcome to your support ticket."
        )
        embed_contenido.set_footer(text="Click the button below to close this ticket")
        contenido = menciones_staff

        await nuevo_ticket.send(content=contenido)
        await nuevo_ticket.send(embed=embed_contenido, view=BotonCerrar())


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MenuTickets())


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')



#### COMANDO PARA ESTABLECER EL PANEL DE TICKES ####

@bot.command()
@commands.has_permissions(administrator=True)
async def ticketpanel(ctx):
    await ctx.message.delete()
    id_canal = 1479546657501745363
    canal = bot.get_channel(id_canal) or await bot.fetch_channel(id_canal)

    embed_ticketpanel = discord.Embed(
        title="Ticket Panel",
        description="Please select a category to open a ticket:",
        color=discord.Color.light_gray(),
        timestamp=datetime.datetime.now()
    )
    embed_ticketpanel.set_author(name="jrr's studio",
                     icon_url="https://media.discordapp.net/attachments/1340021249811939382/1480612688068608132/jrrs_studio.png")
    embed_ticketpanel.set_footer(text="Misuse of tickets may lead to sanctions.")

    await canal.send(embed=embed_ticketpanel, view=TicketView())



#### COMANDO PARA RENOMBRAR UN TICKET ####

@bot.command()
@commands.check_any(commands.has_role(1479548860178108466), commands.has_permissions(administrator=True))
async def rename(ctx, *, new_name: str):

    embed_rename = discord.Embed(
        description=f"Channel renamed to {ctx.channel.mention}",
        color=discord.Color.blue(),
    )
    await ctx.message.delete()
    if ctx.channel.category_id not in CATEGORIAS_TICKETS.values():
        return await ctx.send(embed_errorchanel, delete_after=5)

    formatted_name = new_name.lower().replace(" ", "-")
    await ctx.send(embed=embed_rename)
    try:
        await ctx.channel.edit(name=formatted_name)
    except Exception:
        await ctx.send("An error occurred")



#### COMANGO PARA ELIMINAR CIERTOS MENSAJES ####

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)



embed_errorchanel = discord.Embed(
        description="This channel is not a ticket channel."
    )



#### COMANDO PARA AÑADIR A UN USUARIO A UN TICKET ####

@bot.command()
@commands.check_any(commands.has_role(1479548860178108466), commands.has_permissions(administrator=True))
async def add(ctx, new_user: discord.Member):
    await ctx.message.delete()

    if ctx.channel.category_id in CATEGORIAS_TICKETS.values():
        await ctx.channel.set_permissions(new_user,
                                          view_channel=True,
                                          send_messages=True,
                                          read_message_history=True)

        embed_useradded = discord.Embed(
            description=f"{new_user.mention} has been added to {ctx.channel.mention}",
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed_useradded)
    else:
        await ctx.send(embed=embed_errorchanel, delete_after=5)



#### COMANDO PARA ELIMINAR A UN USUARIO DE UN TICKET ####

@bot.command()
@commands.check_any(commands.has_role(1479548860178108466), commands.has_permissions(administrator=True))
async def remove(ctx, user_deleted: discord.Member):
    await ctx.message.delete()

    if ctx.channel.category_id in CATEGORIAS_TICKETS.values():
        await ctx.channel.set_permissions(user_deleted, overwrite=None)

        embed_userremoved = discord.Embed(
            description=f"{user_deleted.mention} has been removed from {ctx.channel.mention}",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed_userremoved)
    else:
        await ctx.send(embed=embed_errorchanel, delete_after=5)



#### COMANDO PARA CERRAR LOS TICKETS ####

@bot.command()
@commands.check_any(commands.has_role(1479548860178108466), commands.has_permissions(administrator=True))
async def close(ctx):
    if ctx.channel.category_id in CATEGORIAS_TICKETS.values():
        await ctx.message.delete()

        embed_transcript = discord.Embed(
            description=f"Channel closed. Generating transcript...",
            color=discord.Color.purple(),
        )
        await ctx.send(embed=embed_transcript)
        log_content = f"Transcript for {ctx.channel.name}\n"
        log_content += f"Closed by (Command): {ctx.author} ({ctx.author.id})\n"
        log_content += "-" * 30 + "\n"

        async for message in ctx.channel.history(limit=None, oldest_first=True):
            time = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            log_content += f"[{time}] {message.author}: {message.content}\n"

        canal_logs = bot.get_channel(ID_CANAL_TRANSCRIPTS)
        if canal_logs:
            file = discord.File(
                io.BytesIO(log_content.encode()),
                filename=f"transcript-{ctx.channel.name}.txt"
            )
            await canal_logs.send(content=f"Ticket closed via command: **{ctx.channel.name}**", file=file)

        await asyncio.sleep(3)
        await ctx.channel.delete()
    else:
        await ctx.send(embed=embed_errorchanel, delete_after=5)



#### CONFIGURACION DE ANTISPAM ####
canal_prohibido_id = 1480953985203572910


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')


    canal = bot.get_channel(canal_prohibido_id)

    if canal:

        await canal.purge(limit=10, check=lambda m: m.author == bot.user)


        embed_info = discord.Embed(
            title="CANAL ANTI-SPAM BY JRR'S STUDIO BOT",
            description="Cualquier persona que envíe un mensaje por aquí será aislado automáticamente durante 1 semana.",
            color=discord.Color.purple(),
        )
        embed_info.set_author(
            name="jrr's studio",
            icon_url="https://media.discordapp.net/attachments/1340021249811939382/1480612688068608132/jrrs_studio.png"
        )

        await canal.send(embed=embed_info)
        print("Mensaje informativo enviado al canal prohibido.")


@bot.event
async def on_message(message):

    if message.author == bot.user:
        return


    if message.channel.id == canal_prohibido_id:
        usuario = message.author
        ahora = datetime.datetime.now(datetime.timezone.utc)


        try:
            duracion = datetime.timedelta(weeks=1)
            await usuario.timeout(duracion, reason="Spam detection by jrr's studio bot")
        except Exception as e:
            print(f"Error al aislar: {e}")


        hace_una_hora = ahora - datetime.timedelta(hours=1)
        try:
            await message.channel.purge(
                limit=100,
                after=hace_una_hora,
                check=lambda m: m.author == usuario
            )
        except Exception as e:
            print(f"Error al aislar: {e}")

    await bot.process_commands(message)

bot.run(TOKEN)
