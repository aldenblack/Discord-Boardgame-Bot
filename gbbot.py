# Gameboard Bot
import os
import random
from itertools import cycle
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv() 
TOKEN = os.environ.get("TOKEN")
intents=discord.Intents().all()

bot = commands.Bot(command_prefix='gb;', intents=intents)
bot.remove_command("help")

@bot.event
async def on_ready():
	await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name="gb;help"))
	print("Bot is now active.")

# -------------------- COMMANDS --------------------

supported_games = ['amazons', 'amazons10', 'amazons8', 'amazons6']

@bot.command()
async def info(ctx, *, game):
	args = game.split()
	if args[0].lower() in supported_games:
		if args[0].lower() == 'amazons' or args[0].lower() == 'amazons10' or args[0].lower() == 'amazons8' or args[0].lower() == 'amazons6':
			amazonembed = discord.Embed(
			description='Amazons is a two-player boardgame in which players vie for the last move.',
			colour=discord.Colour.blue()
			)
			amazonembed.set_author(name="The Game of Amazons")
			amazonembed.add_field(name="Rules", value="In each move, a player\'s piece can be moved any space diagonally or cardinally from its starting position, and that piece MUST shoot an arrow (with the same legal directions) after moving, which will land on a specified space and render that square uncrossable by arrows and players.", inline=True)
			amazonembed.add_field(name="Strategy", value="In order to have the \"last move\", a player must use their arrows to block the opponent such that each of the opponent\'s pieces is connected to less squares than the player's pieces. Thereby, the player will have more remaining moves left to make once all pieces are blockaded.", inline=True)
			amazonembed.add_field(name="Gameplay", value="Valid responses are any sequence that include a valid letter on the board, followed by a number. A total of 3 are sent in each move, and can be sent in one message or multiple. The first picks which piece is moved, the second choses where to move it, and the third choses where to shoot the arrow. Additionally, writing \"forfeit\" will automatically make the opponent win. Example: a4 d1 d9 (The piece at a4 moves up and to the right, then shoots an arrow to the down.)", inline=False)
			amazonembed.add_field(name="Variants", value="Amazons can be played on a variety of boards, many of which are supported here. Using amazons6, amazons8, or amazons10, you can play variants with each respective board size.")
			amazonembed.set_image(url="https://cdn.discordapp.com/attachments/761396064052838441/761445040232202240/Screen_Shot_2020-10-01_at_9.27.50_PM.png")
			await ctx.send(embed=amazonembed)
	else:
		await ctx.send(f'The game "{game}" is not supported.')

active_challenges = []
active_games = []
silenced_players = [] # Stops you from being challenged. (TODO create gb;silence)

@bot.command()
async def challenge(ctx, *, command):
	# Structure: gb;challenge opponent(s) game
	args = command.split()
	if args[-1] in supported_games: 
		members = []
		for mem in bot.get_all_members():
			if mem not in silenced_players:
				members.append(mem.name) # Doesn't support nicks
		if args[0] in members: # TODO: Make more robust for 2+ player games.
			challenged = False
			for c in active_challenges:
				if [args[-1], ctx.message.author.name, args[0]] == c[:3]:
					challenged = True
			if challenged:
				await ctx.send(f'Already sent {str(args[-1]).capitalize()} challenge to {args[0]}. Use \'gb;challenges\' to view current incoming and outgoing challenges.')
			else:
				active_challenges.append([args[-1], ctx.message.author.name, args[0], 5])
				await ctx.send(f'Challenge queued.')# \nChallenges: {active_challenges}')
		else:
			await ctx.send(f'{args[0]} is not a member of the server.')
	else:
		ctx.send(f'{args[1]} is not a valid game. Use gb;help games for a list of supported games.')

@bot.command()
async def accept(ctx, *, command):
	# Structure: gb;accept challenger game
	args = command.split()
	for challenge in active_challenges: 
		if ctx.message.author.name in challenge:
			if args[1]:
				if args[1] in challenge:
					await ctx.send('Challenge accepted!')
					active_challenges.remove(challenge)
					newgame = Game(challenge)
					active_games.append(newgame)
					newgame.makeboard()
					await ctx.send(f'Starting Amazons game between {ctx.message.author.name} and {args[0]}...')
					await ctx.send(embed=newgame.draw())

				else:
					await ctx.send(f'No pending challenges from {args[1]}.')
			else:
				await ctx.send('Challenge accepted!')
				active_challenges.remove(challenge)
				active_games.append(Game(challenge))
		else:
			await ctx.send('No pending challenges.')

@bot.command()
async def decline(ctx, *, command):
	args = command.split()
	for challenge in active_challenges:
		if ctx.message.author.name in challenge: # fix so you can only decline others'
			if args[1]:
				if args[1] in challenge:
					await ctx.send('Challenge accepted!')
					active_challenges.remove(challenge)
					active_games.append(Game(challenge))
				else:
					await ctx.send(f'No pending challenges from {args[1]}.')
			else:
				await ctx.send('Challenge accepted!')
				active_challenges.remove(challenge)
				active_games.append(Game(challenge))
		else:
			await ctx.send('No pending challenges.')

@bot.command(aliases=['currentgames'])
async def challenges(ctx):
	embed = discord.Embed(
		colour=discord.Colour.orange()
	)
	embed.set_author(name=f"Challenges for {ctx.message.author.name}:")
	incoming=""
	outgoing=""
	ongoing=""
	for challenge in active_challenges:
		if challenge[2] == str(ctx.message.author.name):
			incoming += f" - '{challenge[0]}' with {challenge[1]}.\n"
		if challenge[1] == str(ctx.message.author.name):
			outgoing += f" - '{challenge[0]}' with {challenge[2]}.\n"
	if incoming == "":
		incoming = "`None`" # No challenges here! Why not start a game with someone?
	if outgoing == "":
		outgoing = "`None`"
	if ongoing == "":
		ongoing = "`None`"
	embed.add_field(name="Incoming Challenges", value=incoming, inline=False)
	embed.add_field(name="Outgoing Challenges", value=outgoing, inline=False)
	embed.add_field(name="Ongoing Games", value=ongoing, inline=False)
	await ctx.send(embed=embed)



@tasks.loop(seconds=10) # 4-5 min timer on challenges.
async def challenge_cooldown():
	for challenge in active_challenges:
		challenge[3] -= 1
		if challenge[3] == 0:
			active_challenges.remove(challenge)
	await ctx.send(active_challenges)

# -------------------- AMAZONS --------------------

class Boardspace:
	north = None
	south = None
	east = None
	west = None
	northeast = None
	northwest = None
	southeast = None
	southwest = None

	piece = None 
	pos = None

	def addpiece(self, piece):
		if self.piece == None:
			self.piece = piece
		else:
			return False
		return True

	def addpos(self, x, y):
		self.pos = (x, y)


class Piece:
	team = False # True is White, False is Black
	boardpos = None # Boardspace object.

	def __init__(self, team, pos):
		self.team = team
		self.boardpos = pos

	def valid_moves(self):
		result = {self.boardpos.pos}

class Amazon(Piece):
	def __init__(self, team, pos):
		super().__init__(team, pos)

	def valid_moves(self):
		result = set() 

		space = self.boardpos.north
		while space and not space.piece:
			result.add(space.pos)
			space = space.north

		space = self.boardpos.south
		while space and not space.piece:
			result.add(space.pos)
			space = space.south

		space = self.boardpos.east
		while space and not space.piece:
			result.add(space.pos)
			space = space.east

		space = self.boardpos.west
		while space and not space.piece:
			result.add(space.pos)
			space = space.west

		space = self.boardpos.northeast
		while space and not space.piece:
			result.add(space.pos)
			space = space.northeast

		space = self.boardpos.northwest
		while space and not space.piece:
			result.add(space.pos)
			space = space.northwest

		space = self.boardpos.southeast
		while space and not space.piece:
			result.add(space.pos)
			space = space.southeast

		space = self.boardpos.southwest
		while space and not space.piece:
			result.add(space.pos)
			space = space.southwest

		return result

	def move(self, newpos, board): 
		if self.boardpos.pos == newpos:
			return False

		moveto = board[newpos[0]][newpos[1]]
		moveto.addpiece(self)
		self.boardpos.piece = None 
		self.boardpos = moveto
		return True

	def fire(self, newpos, board):
		if self.boardpos.pos == newpos:
			return False

		fireto = board[newpos[0]][newpos[1]]
		fireto.addpiece(AmazonArrow(newpos))

	def is_dead(self):
		return self.valid_moves() == set()

class AmazonArrow(Piece): 
	def __init__(self, pos):
		super().__init__(None, pos) 




movedict = {'a': 0, 'b': 1, 'c': 2, 'd': 3, 'e': 4, 'f': 5, 'g': 6, 'h': 7, 'i': 8, 'j': 9, '1': 0, '2': 1, '3': 2, '4': 3, '5': 4, '6': 5, '7': 6, '8': 7, '9': 8, '0': 9}
gameboarddict = {0: 'one', 1: 'two', 2: 'three', 3: 'four', 4: 'five', 5: 'six', 6: 'seven', 7: 'eight', 8: 'nine', 9: 'zero', }
class Game():
	mode = None
	players = []
	current_player = None
	other_player = None
	current_move = 0
	state = 0

	def __init__(self, challenge_tag):
		self.mode = challenge_tag[0]
		self.players = [challenge_tag[1], challenge_tag[2]]
		self.current_player = self.players[0]
		self.other_player = self.players[1]
		self.current_move = 0
		self.state = 0 # State is val 1-3 for select piece, move piece, fire arrow in draw()
		self.selected = None
		self.validmoves = set()
		self.gameboard = []
		self.color = 'Blue'
		self.prevselect = ''
		self.originalpos = (0, 0) # The position the piece started at, for undo history

	def play(self):
		self.current_move += 1
		self.state = 0
		self.current_player, self.other_player = self.other_player, self.current_player
		if self.current_move%2 == 0:
			self.color = 'Blue'
		else:
			self.color = 'Red'


	def parse(self, inps):
		movestring = ""
		print('Parsing.')
		inp = inps.split()
		while inp:
			if inp[0].lower() == "undo":
				if self.state == 2:
					self.selected.move(self.originalpos, self.gameboard)
				self.selected = None 
				self.validmoves = set() 
				self.state = 0
				movestring += 'Undid move.\n'
				inp.pop(0)
			else:
				print(inp[0])
				print(movedict[inp[0][0]], movedict[inp[0][1]])
				if len(inp[0]) == 2:
					if inp[0][0] in movedict and inp[0][1] in movedict:
						x, y = movedict[inp[0][1]], movedict[inp[0][0]]
					else:
						return movestring + 'Invalid move; input position must be on the board.'
				else: # Return on error.
					return movestring + 'Invalid move; input must be a position of the form (letter)(number).'
			
				if self.state == 0:
					if self.gameboard[x][y].piece:
						if self.gameboard[x][y].piece.team == self.current_move%2: # If false, 0 and Blue. If true, 1 and Red.
							movestring += f'{self.color} amazon {inp[0].capitalize()} selected.\n'
							self.originalpos = (x, y)
							self.selected = self.gameboard[x][y].piece
							self.validmoves = self.selected.valid_moves() 
							self.prevselect = inp.pop(0)
							self.state += 1
						else:
							return movestring + 'Piece is of the wrong team.'
					else:
						return movestring + 'No piece in that space.'
				elif self.state == 1:
					if (x, y) in self.validmoves:
						movestring += f'{self.color} amazon {self.prevselect.capitalize()} moved to {inp[0].capitalize()}.\n'
						self.selected.move((x, y), self.gameboard)
						print("Moving to", x, y)
						self.validmoves = self.selected.valid_moves()
						self.prevselect = inp.pop(0)
						self.state += 1
					else:
						return movestring + 'Invalid move; that piece cannot move there.'
				else:
					if (x, y) in self.validmoves:
						movestring += f'{self.color} amazon {self.prevselect.capitalize()} fires to {inp[0].capitalize()}.\n' 
						self.selected.fire((x, y), self.gameboard)
						self.play()
						inp = [] # Clears input so it only acts for one full turn total
						movestring += f'{self.color}\'s turn.' 
						self.selected = None
						self.validmoves = set()
					else:
						return movestring + 'Invalid move; amazon cannot fire arrow there.'
		return movestring



	def makeboard(self):
		if self.mode == 'amazons10' or 'amazons':
			board = [[Boardspace() for i in range(10)] for j in range(10)]
			for i in range(10):
				for j in range(10):
					curr = board[i][j]
					curr.addpos(i, j) # Setting adjacent positions: 
					curr.north = board[i-1][j] if i-1 >= 0 else None 
					curr.south = board[i+1][j] if i+1 <= 9 else None 
					curr.west = board[i][j-1] if j-1 >= 0 else None
					curr.east = board[i][j+1] if j+1 <= 9 else None
					curr.northeast = board[i-1][j+1] if (i-1 >= 0) and (j+1 <=9) else None
					curr.northwest = board[i-1][j-1] if (i-1 >= 0) and (j-1 >=0) else None
					curr.southeast = board[i+1][j+1] if (i+1 <= 9) and (j+1 <=9) else None
					curr.southwest = board[i+1][j-1] if (i+1 <= 9) and (j-1 >=0) else None

					if i == 0 and (j == 3 or j == 6):
						newpiece = Amazon(True, curr)
						curr.addpiece(newpiece)
					if i == 3 and (j == 0 or j == 9):
						newpiece = Amazon(True, curr)
						curr.addpiece(newpiece)
					if i == 6 and (j == 0 or j == 9):
						newpiece = Amazon(False, curr)
						curr.addpiece(newpiece)
					if i == 9 and (j == 3 or j == 6):
						newpiece = Amazon(False, curr)
						curr.addpiece(newpiece)

		elif self.mode == 'amazons8':
			board = [[Boardpos() for i in range(8)] for j in range(8)]
		elif self.mode == 'amazons6':
			board = [[Boardpos() for i in range(6)] for j in range(6)]
		
		self.gameboard = board

	def draw(self):
		if self.mode == 'amazons10' or 'amazons':
			gb = "💠 🇦 🇧 🇨 🇩 🇪 🇫 🇬 🇭 🇮 🇯💠"
			print("Valid moves:", self.validmoves)
			for row in range(len(self.gameboard)):
				gb += f"\n :{gameboarddict[row]}: "
				for space in self.gameboard[row]:
					if space.piece:
						if space.piece.team == None: 
							gb += "🔥 "
						elif space.piece.team == True:
							gb += "🟥 " 
						else:
							gb += "🟦 " 
					else: 
						if space.pos in self.validmoves: 
							gb += "🟪 "
						elif row%2 == 0:
							if space.pos[1]%2 == 0: 
								gb += "⬜ "
							else:
								gb += "⬛ "
						else:
							if space.pos[1]%2 == 0:
								gb += "⬛ "
							else:
								gb += "⬜ "
				gb += "  |"
			gb += "\n 💠 ———————————————— 💠"
		
		if self.state == 0:
			actionqueue = "Select Piece | Move Piece | Fire Arrow"
		elif self.state == 1:
			actionqueue = "Move Piece | Fire Arrow"
		else:
			actionqueue = "Fire Arrow"
		gamewindow = discord.Embed(
			title=f"{self.color}'s move",
			description=gb,
			colour=discord.Colour.blue() if self.current_move%2 == 0 else discord.Colour.red() # Changes according to player
		)
		gamewindow.set_author(name=f'{self.players[0]} vs. {self.players[1]} - {self.mode.capitalize()}')
		gamewindow.add_field(name='Action Queue', value=actionqueue)

		return gamewindow



@bot.listen('on_message')
async def gameplay_move(message):
	for game in active_games:
		if message.author.name in game.players:
			print(message.content)
			if message.author.name == game.current_player:
				if message.content == 'forfeit':
					active_games.remove(game)
					await message.channel.send(f"{game.other_player} wins! `0 {game.current_player} | {game.other_player} 1`")
				if len(message.content) <= 9:
					await message.channel.send(game.parse(message.content))
					await message.channel.send(embed=game.draw())
					# Action queue: Select Piece | Move Piece | Fire Arrow :determined by game.state
			elif message.author.name == game.other_player:
				if message.content == 'forfeit':
					active_games.remove(game)
					await message.channel.send(f"{game.current_player} wins! `1 {game.current_player} | {game.other_player} 0`")



@bot.command()
async def ev(ctx, *, commands):
	await ctx.send(eval(commands))


@bot.command(pass_context=True)
async def help(ctx, *, command=""):
	author = ctx.message.author
	embed = discord.Embed(
		colour=discord.Colour.orange()
	)
	
	embed.set_author(name="GB Help", icon_url="https://media.discordapp.net/attachments/759238353416618005/760755487296847892/24876.b9db3b03.1200x674o.78f9ae1d0f18.jpg")
	embed.add_field(name="Games", value="Amazons", inline=False)
	embed.add_field(name="Commands", value="`info <game>`: Displays overview and help for a game.\n\n`challenge <player> <game>`: Open a challenge with a new opponent.\n\n`challenges` or `currentgames`: Display your incoming, outgoing, and ongoing games.\n\n`accept <player> <game>`: Accept a challenge and start a new game.\n\n`silence <player>`: (TBA) Block a player from sending challenges.", inline=False)
	
	await author.send(embed=embed)
# TODO: declineall, removechallenge, silence



bot.run(TOKEN)