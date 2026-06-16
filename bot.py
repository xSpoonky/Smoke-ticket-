import os
import json
import re
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")

SOLLICITATIE_CATEGORY_ID = int(os.getenv("SOLLICITATIE_CATEGORY_ID"))
ZAKENPARTNER_CATEGORY_ID = int(os.getenv("ZAKENPARTNER_CATEGORY_ID"))

LEAD_ROLE_ID = int(os.getenv("LEAD_ROLE_ID"))
SMOKE_ROLE_ID = int(os.getenv("SMOKE_ROLE_ID"))

MAX_PLEKKEN = 25
STATUS_FILE = "status_message_data.json"

status_channel_id = None
status_message_id = None

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


def save_status(channel_id, message_id):
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump({"channel_id": channel_id, "message_id": message_id}, f)
    except Exception as e:
        print(f"Kon status niet opslaan: {e}")


def load_status():
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None


def veilige_naam(naam):
    naam = naam.lower().replace(" ", "-")
    naam = re.sub(r"[^a-z0-9-]", "", naam)
    return naam[:80] or "gebruiker"


def tel_smoke_leden(guild):
    smoke_role = guild.get_role(SMOKE_ROLE_ID)
    if smoke_role is None:
        return 0
    return len(smoke_role.members)


async def maak_status_tekst(guild):
    aantal_smoke = tel_smoke_leden(guild)
    plekken_over = max(MAX_PLEKKEN - aantal_smoke, 0)

    if plekken_over == 0:
        emoji = "🔴"
        status = "GESLOTEN"
        uitleg = "Momenteel kom je in een wachtrij. De groep zit op dit moment vol."
    elif plekken_over <= 5:
        emoji = "🟠"
        status = "BEPERKT BESCHIKBAAR"
        uitleg = "Er zijn momenteel nog maar weinig plekken beschikbaar."
    else:
        emoji = "🟢"
        status = "OPEN"
        uitleg = "Sollicitaties staan momenteel open. Je kunt een ticket aanmaken."

    return f"""📋 **Sollicitatie Informatie**

{emoji} **Status:** {status}

{uitleg}

———

✅ **Sollicitatie-eisen**

🔞 16+ ( Jonger dan 15 = ticket direct gesloten)   

💰 Minimale waarde: €7.000.000

🔫 Minimaal 2 vuurwapens in bezit

🎥 Clips verplicht

🧠 Volwassen mindset, houding en gedrag

🗣️ Respectvolle communicatie

🤝 Loyaliteit en professionaliteit

⏰ Actieve aanwezigheid binnen de organisatie

———

📌 **Belangrijk**

Niet voldoen aan één of meerdere eisen kan leiden tot afwijzing van de sollicitatie.

**Status legenda:**

• 🟢 Open
• 🟠 Beperkt beschikbaar
• 🔴 Gesloten

**Huidige status:** {emoji} **{status}**

**Beschikbare plekken:** {plekken_over} plekken over!
"""


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Zakenpartner",
        emoji="💼",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_zakenpartner"
    )
    async def zakenpartner(self, interaction: discord.Interaction, button: discord.ui.Button):
        await maak_ticket(interaction, "zakenpartner")

    @discord.ui.button(
        label="Sollicitatie",
        emoji="📄",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_sollicitatie"
    )
    async def sollicitatie(self, interaction: discord.Interaction, button: discord.ui.Button):
        await maak_ticket(interaction, "sollicitatie")


class CloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Ticket sluiten",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_sluiten"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Ticket wordt gesloten...", ephemeral=True)
        await interaction.channel.delete()


async def maak_ticket(interaction: discord.Interaction, soort: str):
    guild = interaction.guild
    lead_role = guild.get_role(LEAD_ROLE_ID)
    bot_member = guild.me

    if soort == "sollicitatie":
        category = guild.get_channel(SOLLICITATIE_CATEGORY_ID)
    else:
        category = guild.get_channel(ZAKENPARTNER_CATEGORY_ID)

    if category is None:
        await interaction.response.send_message("❌ Ticketcategorie niet gevonden.", ephemeral=True)
        return

    if lead_role is None:
        await interaction.response.send_message("❌ Sollicitatie behandelaar rol niet gevonden.", ephemeral=True)
        return

    gebruikersnaam = veilige_naam(interaction.user.name)
    kanaal_naam = f"{soort}-{gebruikersnaam}"

    bestaand_kanaal = discord.utils.get(guild.channels, name=kanaal_naam)
    if bestaand_kanaal:
        await interaction.response.send_message(
            f"❌ Je hebt al een ticket: {bestaand_kanaal.mention}",
            ephemeral=True
        )
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        ),
        lead_role: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        ),
        bot_member: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True
        )
    }

    kanaal = await guild.create_text_channel(
        name=kanaal_naam,
        category=category,
        overwrites=overwrites
    )

    if soort == "zakenpartner":
        tekst = f"""🤝 **Zakenpartner Aanvraag**

Welkom {interaction.user.mention}!

**Wie zijn jullie?**

**Hoelang bestaan de groep al?**

**Is de groep al gekend in de stad?**

**Wat heb je te bieden?**

**Wat verwacht je van ons?**
"""
    else:
        tekst = f"""📄 **Sollicitatie Formulier**

Welkom {interaction.user.mention}!

**IRL-Naam:**
**Leeftijd:**
**In-Game Naam:**

**Motivatie (50+ woorden):**
Waarom wil je lid worden van onze gang?

**Verwachtingen:**
Wat kunnen wij van jou verwachten?

**Ervaring:**
Heb je ervaring binnen andere organisaties? Zo ja, welke?

**Bezittingen:**
Welke voertuigen, wapens en hoeveel geld bezit je momenteel?

**Activiteit:**
Hoe vaak ben je online?

**Clips:**
Voeg hier je beste clips toe.

**Extra:**
Extra dingen die wij van jou zouden moeten weten.
"""

    await kanaal.send(tekst, view=CloseView())

    await kanaal.send(
        f"📢 **Als je dit liever mondeling wilt doen laat het zeker weten.**"
    )

    await interaction.response.send_message(
        f"✅ Je ticket is geopend: {kanaal.mention}",
        ephemeral=True
    )


async def update_status(guild):
    global status_channel_id, status_message_id

    if status_channel_id is None or status_message_id is None:
        return

    channel = bot.get_channel(status_channel_id)
    if channel is None:
        return

    try:
        bericht = await channel.fetch_message(status_message_id)
        await bericht.edit(content=await maak_status_tekst(guild))
    except Exception as e:
        print(f"Status update fout: {e}")


@bot.command()
@commands.has_permissions(administrator=True)
async def ticketpanel(ctx):
    global status_channel_id, status_message_id

    try:
        await ctx.message.delete()
    except:
        pass

    status_bericht = await ctx.send(await maak_status_tekst(ctx.guild))

    status_channel_id = ctx.channel.id
    status_message_id = status_bericht.id
    save_status(status_channel_id, status_message_id)

    ticket_embed = discord.Embed(
        title="🎟️ Tickets",
        description=(
            "Maak hier je ticket aan voor het volgende:\n\n"
            "• 💼 Zakenpartner\n\n"
            "• 📄 Sollicitatie"
        ),
        color=0x2B2D31
    )

    await ctx.send(embed=ticket_embed, view=TicketView())


@bot.event
async def on_ready():
    global status_channel_id, status_message_id

    bot.add_view(TicketView())
    bot.add_view(CloseView())

    data = load_status()
    if data:
        status_channel_id = data.get("channel_id")
        status_message_id = data.get("message_id")

        for guild in bot.guilds:
            await update_status(guild)

    print(f"Ingelogd als {bot.user}")


@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        await update_status(after.guild)


@bot.event
async def on_member_join(member):
    await update_status(member.guild)


@bot.event
async def on_member_remove(member):
    await update_status(member.guild)


bot.run(TOKEN)
