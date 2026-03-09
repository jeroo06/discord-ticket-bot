import os
import discord
from discord.ext import commands
import datetime
from dotenv import load_dotenv
import io
import asyncio

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# --- CONFIGURATION ---
CATEGORIAS_TICKETS = {
    "Support": 1480645721672912986,
    "Partner": 1480646025176944752,
    "Highlight": 1480645883346419787
}
ID_CANAL_TRANSCRIPTS = 1479931001089163465

# NUEVO: Lista de IDs de roles que pueden ver los tickets
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

        contenido = (
            f"🎫 **New {categoria_nombre} Ticket**\n"
            f"Hello {usuario.mention}, welcome to your support ticket.\n"
            f"The staff team {menciones_staff} will assist you shortly.\n\n"
            f"Click the button below to close this ticket."
        )

        await nuevo_ticket.send(content=contenido, view=BotonCerrar())


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MenuTickets())


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')


@bot.command()
@commands.has_permissions(administrator=True)
async def ticketpanel(ctx):
    await ctx.message.delete()
    id_canal = 1480609045281902834
    canal = bot.get_channel(id_canal) or await bot.fetch_channel(id_canal)

    embed = discord.Embed(
        title="Ticket Panel",
        description="Please select a category to open a ticket:",
        color=discord.Color.green(),
        timestamp=datetime.datetime.now()
    )
    embed.set_author(name="JrrStudio",
                     icon_url="https://media.discordapp.net/attachments/1340021249811939382/1480612688068608132/jrrs_studio.png")
    embed.set_footer(text="Misuse of tickets may lead to sanctions.")

    await canal.send(embed=embed, view=TicketView())


@bot.command()
@commands.has_permissions(manage_channels=True)
async def rename(ctx, *, new_name: str):
    await ctx.message.delete()
    if ctx.channel.category_id not in CATEGORIAS_TICKETS.values():
        return await ctx.send("❌ This command can only be used inside a ticket channel.", delete_after=5)

    formatted_name = new_name.lower().replace(" ", "-")
    try:
        await ctx.channel.edit(name=formatted_name)
    except Exception:
        await ctx.send("An error occurred")


@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)


bot.run(TOKEN)