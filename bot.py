import discord
from discord.ext import commands
import os
import random
from logic import Pokemon, Player, Enemy # Assuming these classes are well-defined

# Cek keberadaan config.py, jika tidak ada, gunakan environment variable
try:
    from config import TOKEN
except ImportError:
    TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Menyimpan data pemain
players = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")

## Game Commands

@bot.command()
async def start(ctx):
    embed = discord.Embed(
        title="Welcome to Pokemon Adventure Bot!",
        description="This is a Pokemon adventure game. Start by claiming your first Pokemon with the `!claim` command!",
        color=0x7289DA # Discord's brand color
    )
    await ctx.send(embed=embed)

@bot.command()
async def claim(ctx, choice: str = None):
    user_id = str(ctx.author.id)

    if user_id in players:
        embed = discord.Embed(
            title="Already Claimed!",
            description=f"{ctx.author.mention}, you already have a Pokemon: **{players[user_id].pokemon.name}**!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    starters = {
        "charmander": ("Charmander", 20, 100),
        "squirtle": ("Squirtle", 18, 110),
        "bulbasaur": ("Bulbasaur", 19, 105)
    }

    if choice is None or choice.lower() not in starters:
        options = ", ".join([f"`{s}`" for s in starters.keys()])
        embed = discord.Embed(
            title="Choose Your Starter Pokemon!",
            description=f"{ctx.author.mention}, please choose your starter Pokemon using `!claim <name>`.\n"
                        f"For example: `!claim charmander`\n\n"
                        f"Available options: {options}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return

    selected = starters[choice.lower()]
    pokemon = Pokemon(selected[0], selected[1], selected[2])
    player = Player(ctx.author.name, pokemon)
    players[user_id] = player

    embed = discord.Embed(
        title=f"Congratulations, {ctx.author.name}!",
        description=f"You have chosen **{pokemon.name}**!",
        color=discord.Color.green()
    )
    embed.add_field(name="HP", value=f"{pokemon.hp}/{pokemon.max_hp}", inline=True)
    embed.add_field(name="Power", value=str(pokemon.power), inline=True)
    embed.set_footer(text="Use !stats to see your Pokemon's status and !battle to fight!")
    await ctx.send(embed=embed)

@bot.command()
async def stats(ctx):
    user_id = str(ctx.author.id)

    if user_id not in players:
        embed = discord.Embed(
            title="No Pokemon Found",
            description=f"{ctx.author.mention}, you don't have a Pokemon yet! Use `!claim` to get one.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    player = players[user_id]
    pokemon = player.pokemon

    embed = discord.Embed(
        title=f"Pokemon Stats: {pokemon.name}",
        color=0x00ff00 # Green
    )
    embed.set_author(name=f"Trainer: {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    embed.add_field(name="HP", value=f"{pokemon.hp}/{pokemon.max_hp}", inline=True)
    embed.add_field(name="Power", value=str(pokemon.power), inline=True)
    embed.add_field(name="Battle Record", value=f"Wins: {player.wins}\nLosses: {player.losses}", inline=False)
    await ctx.send(embed=embed)

## Battle System with Buttons

class BattleView(discord.ui.View):
    def __init__(self, player_id):
        super().__init__(timeout=180) # Timeout after 3 minutes if no interaction
        self.player_id = player_id

    @discord.ui.button(label="Attack", style=discord.ButtonStyle.red, emoji="⚔️")
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.player_id:
            await interaction.response.send_message("This isn't your battle!", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        player = players[user_id]
        enemy = player.current_enemy

        if not enemy or not enemy.pokemon.is_alive():
            await interaction.response.send_message("This battle is over or you're not in one! Use `!battle` to start a new one.", ephemeral=True)
            self.stop() # Stop the view if battle is over
            return

        response_messages = []

        # Player attacks
        damage_dealt = player.attack_enemy(enemy)
        response_messages.append(f"{player.pokemon.name} attacked {enemy.pokemon.name} and dealt **{damage_dealt}** damage!")

        if not enemy.pokemon.is_alive():
            # Player wins
            hp_increase = 10 + random.randint(5, 15)
            power_increase = 1 + random.randint(0, 2)
            player.pokemon.increase_stats(hp_increase, power_increase)
            player.add_win()

            response_messages.append(f"🎉 **Victory!** You defeated {enemy.pokemon.name}!")
            response_messages.append(f"Your Pokemon gained **+{hp_increase} HP** and **+{power_increase} Power**.")
            response_messages.append(f"Current stats: HP {player.pokemon.hp}/{player.pokemon.max_hp}, Power: {player.pokemon.power}")
            response_messages.append(f"Total wins: {player.wins}")

            if player.wins % 5 == 0:
                player.pokemon.increase_stats(10, 5) # Apply bonus immediately
                response_messages.append("✨ **Bonus!** Your Pokemon gained an extra **+10 HP** and **+5 Power** for reaching a multiple of 5 wins!")

            player.current_enemy = None
            self.stop() # Stop the view on victory
            embed_color = discord.Color.green()
        else:
            # Enemy attacks back
            enemy_damage = enemy.pokemon.attack(player.pokemon)
            response_messages.append(f"{enemy.pokemon.name} attacked back and dealt **{enemy_damage}** damage to your Pokemon!")

            if not player.pokemon.is_alive():
                # Player loses
                hp_decrease = 5 + random.randint(0, 5)
                power_decrease = random.randint(0, 1)
                player.pokemon.decrease_stats(hp_decrease, power_decrease)
                player.add_loss()

                response_messages.append(f"😭 **Defeat!** Your Pokemon was knocked out by {enemy.pokemon.name}!")
                response_messages.append(f"Your Pokemon lost **-{hp_decrease} max HP** and **-{power_decrease} Power**.")

                heal_amount = player.pokemon.max_hp // 2
                player.pokemon.heal(heal_amount)
                response_messages.append(f"Your Pokemon has been partially healed. Current HP: **{player.pokemon.hp}/{player.pokemon.max_hp}**")
                response_messages.append(f"Total losses: {player.losses}")

                player.current_enemy = None
                self.stop() # Stop the view on defeat
                embed_color = discord.Color.red()
            else:
                # Battle continues
                response_messages.append(f"\nYour Pokemon: HP {player.pokemon.hp}/{player.pokemon.max_hp}")
                response_messages.append(f"Enemy {enemy.pokemon.name}: HP {enemy.pokemon.hp}")
                embed_color = discord.Color.gold() # Yellow for ongoing battle

        embed = discord.Embed(
            title="Battle Log",
            description="\n".join(response_messages),
            color=embed_color
        )
        embed.set_footer(text="Keep attacking or run!")
        await interaction.response.edit_message(embed=embed, view=self if not self.is_finished() else None)


    @discord.ui.button(label="Run", style=discord.ButtonStyle.gray, emoji="🏃")
    async def run_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.player_id:
            await interaction.response.send_message("This isn't your battle!", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        player = players[user_id]

        if not hasattr(player, 'current_enemy') or player.current_enemy is None:
            await interaction.response.send_message("You are not currently in a battle to run from!", ephemeral=True)
            return

        player.add_loss()
        player.current_enemy = None

        embed = discord.Embed(
            title="Fled Battle",
            description=f"{interaction.user.mention}, you successfully fled from the battle!\n"
                        f"Total losses: {player.losses}",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

@bot.command()
async def battle(ctx):
    user_id = str(ctx.author.id)

    if user_id not in players:
        embed = discord.Embed(
            title="No Pokemon Found",
            description=f"{ctx.author.mention}, you don't have a Pokemon yet! Use `!claim` to get one.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    player = players[user_id]

    if hasattr(player, 'current_enemy') and player.current_enemy is not None:
        embed = discord.Embed(
            title="Already in Battle",
            description=f"{ctx.author.mention}, you are already in a battle with {player.current_enemy.pokemon.name}! Use the buttons to continue or run.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return

    enemies = [
        ("Pidgey", 15, 80), ("Rattata", 17, 70), ("Zubat", 14, 75), ("Caterpie", 13, 65),
        ("Spearow", 16, 85), ("Ekans", 18, 90), ("Sandshrew", 20, 95), ("Nidoran", 19, 85),
        ("Growlithe", 25, 110), ("Poliwag", 22, 105)
    ]

    enemy_power_factor = min(1.5, 0.8 + (player.wins * 0.05))
    enemy_data = random.choice(enemies)
    enemy_name = enemy_data[0]
    enemy_power = int(enemy_data[1] * enemy_power_factor)
    enemy_hp = int(enemy_data[2] * enemy_power_factor)

    enemy_pokemon = Pokemon(enemy_name, enemy_power, enemy_hp)
    enemy = Enemy(f"Wild {enemy_name}", enemy_pokemon)
    player.current_enemy = enemy

    embed = discord.Embed(
        title="Wild Pokemon Encountered!",
        description=f"{ctx.author.mention}, a wild **{enemy_pokemon.name}** appeared!\n\n"
                    f"**Your Pokemon:** {player.pokemon.name} (HP: {player.pokemon.hp}/{player.pokemon.max_hp}, Power: {player.pokemon.power})\n"
                    f"**Wild {enemy_pokemon.name}:** (HP: {enemy_pokemon.hp}, Power: {enemy_pokemon.power})",
        color=discord.Color.purple()
    )
    embed.set_footer(text="What will you do?")

    view = BattleView(str(ctx.author.id))
    await ctx.send(embed=embed, view=view)



@bot.command()
async def heal(ctx):
    user_id = str(ctx.author.id)

    if user_id not in players:
        embed = discord.Embed(
            title="No Pokemon Found",
            description=f"{ctx.author.mention}, you don't have a Pokemon yet! Use `!claim` to get one.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    player = players[user_id]

    if hasattr(player, 'current_enemy') and player.current_enemy is not None:
        embed = discord.Embed(
            title="Cannot Heal During Battle",
            description=f"{ctx.author.mention}, you cannot heal your Pokemon while in a battle! Finish or run from the current battle first.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return

    if player.pokemon.hp >= player.pokemon.max_hp:
        embed = discord.Embed(
            title="Full HP",
            description=f"{ctx.author.mention}, your Pokemon already has full HP!",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return

    heal_amount = player.pokemon.max_hp // 2
    old_hp = player.pokemon.hp
    player.pokemon.heal(heal_amount)

    embed = discord.Embed(
        title="Pokemon Healed!",
        description=f"{ctx.author.mention}, your Pokemon has been healed!\n"
                    f"HP before: **{old_hp}/{player.pokemon.max_hp}**\n"
                    f"HP now: **{player.pokemon.hp}/{player.pokemon.max_hp}**",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name="bantu")
async def bantu(ctx):
    embed = discord.Embed(
        title="Pokemon Adventure Bot - Commands",
        description="Here are all the commands you can use to play!",
        color=0x3498db # Blue
    )
    embed.add_field(name="Getting Started", value="`!start` - Get started with the bot\n`!claim <starter_name>` - Claim your first Pokemon (e.g., `!claim charmander`)", inline=False)
    embed.add_field(name="Pokemon Management", value="`!stats` - View your Pokemon's current stats and battle record\n`!heal` - Restore your Pokemon's HP (cannot be used during battle)", inline=False)
    embed.add_field(name="Battling", value="`!battle` - Find a wild Pokemon to fight (buttons will appear for Attack/Run)", inline=False)
    embed.add_field(name="Admin Commands (Admin Only)", value="`!setwins <amount>` - Set your current wins (for testing/admin purposes)\n`!claimpluh` - Claim a special 'Pluh' Pokemon", inline=False)
    embed.set_footer(text="Have fun on your Pokemon adventure!")
    await ctx.send(embed=embed)

## Admin Commands

@bot.command()
@commands.has_permissions(administrator=True)
async def setwins(ctx, jumlah: int):
    user_id = str(ctx.author.id)

    if user_id not in players:
        await ctx.send(f"{ctx.author.mention}, kamu belum memiliki Pokemon.")
        return

    player = players[user_id]
    previous_wins = player.wins
    player.wins = jumlah

    # Calculate total multiples of 5, new vs. old
    prev_bonus_multiples = previous_wins // 5
    new_bonus_multiples = jumlah // 5
    delta_multiples = new_bonus_multiples - prev_bonus_multiples

    response_msg = f"{ctx.author.mention}, your total wins have been set to **{jumlah}**."

    if delta_multiples > 0:
        total_hp_increase = 10 * delta_multiples
        total_power_increase = 5 * delta_multiples
        player.pokemon.increase_stats(total_hp_increase, total_power_increase)
        response_msg += f" Bonus stats applied: **+{total_hp_increase} HP** and **+{total_power_increase} Power**."
    else:
        response_msg += " No bonus stats were applied."

    embed = discord.Embed(
        title="Wins Set (Admin)",
        description=response_msg,
        color=discord.Color.dark_purple()
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def claimpluh(ctx):
    user_id = str(ctx.author.id)

    if user_id in players:
        embed = discord.Embed(
            title="Already Claimed!",
            description=f"{ctx.author.mention}, you already have a Pokemon: **{players[user_id].pokemon.name}**!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    pokemon = Pokemon("Pluh", 500, 500)
    player = Player(ctx.author.name, pokemon)
    players[user_id] = player

    embed = discord.Embed(
        title=f"Special Pokemon Obtained!",
        description=f"{ctx.author.mention}, you have received the special Pokemon **Pluh**!\n"
                    f"Status: HP {pokemon.hp}/{pokemon.max_hp}, Power: {pokemon.power}",
        color=0xFFD700 # Gold
    )
    await ctx.send(embed=embed)

if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: Discord token not found. Make sure there's a config.py file with TOKEN or a DISCORD_TOKEN environment variable.")
