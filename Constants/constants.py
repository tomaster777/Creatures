# constants.py
# Description: constants.
# ---------------------------------------------------------------------------------------------------------------------

# Debug
DEBUG = True
TEXT_INFORMATION = True

# Object strings.
DNA_STRING = """
Dna
Input  Nodes: {}
Hidden Nodes: {}
Output Nodes: {}

---  Connections ---
{}
--------------------
"""

# Amount of "#" meaning: 1 -> Node number, 2 -> Connection number, 3 -> Mutation number.
CONNECTION_STRING = "<Connection ##{}({}): #{} ==({:.2f})=> #{}>"
NODE_STRING = "<{} #{} bias: {:.3f}>"
BASE_MUTATION_STRING = "<{} :: {}>"
NUMBERED_MUTATION_STRING = "<{} ###{}:: {}>"
WEIGHT_MUTATION_STRING = "<Connection ##{}: #{} -({:.2f} => {:.2f})-> #{}>"
BIAS_MUTATION_STRING = "<{} #{} bias: {:.3f} => {:.3f}>"
NODE_MUTATION_STRING = "<Split: {} | Src: {} | Node: {} | dst: {}>"
CREATURE_STRING = "{} ({} Hidden)"

# Graphics.
CAPTION = 'Creatures'
TEXT_ONLY = True
WINDOW_WIDTH, WINDOW_HEIGHT = 800, 600
FRAME_RATE = 30
CAMERA_SPEED, CAMERA_WIDTH, CAMERA_HEIGHT = 3, 600, 500
WORLD_BORDER = 5
CENTER = 0  # Defines drawing ellipse from their center.

# Simulation.
SIMULATION_WIDTH, SIMULATION_HEIGHT = 3000, 3000
FOOD_TIME_START = 30  # Seconds.
SIMULATION_REPORT = "Generation {} | simulation time: {} | population {} | species {} | current best {}"
PRINT_FREQUENCY = 10  # Frames.

# Colors.
BLACK = 0, 0, 0
GREY = 125, 125, 125
WHITE = 255, 255, 255
RED = 255, 0, 0
GREEN = 0, 255, 0
BLUE = 0, 0, 255
BACKGROUND = 230, 220, 50
SIMULATION_BACKGROUND = 100, 220, 90
PINK = 255, 0, 255
CYAN = 0, 255, 255
PURPLE = 128, 0, 128
ORANGE = 128, 0, 128
FOOD_COLOR = ORANGE

# - Creature -
# Will be used to visually differentiate between species.
CREATURE_COLORS = {
    'RED': RED,
    'GREEN': GREEN,
    'BLUE': BLUE,
    'PINK': PINK,
    'CYAN': CYAN,
    'PURPLE': PURPLE,
    'ORANGE': ORANGE
}

# Outline how to draw the shape.
# For example body = [[(0, 0, 100, 100)], [(0, 100, 20, 20)]]
# The first list is all ellipses with the PRIMARY color, [(0, 0, 100, 100)].
# The second list is all ellipses with the SECONDARY color, [(0, 100, 20, 20)]. And so on and so forth.
CREATURE_REACH = 100
SPEED_SCALING = 0.1
CREATURE_SCALE = 0.05
CREATURE_LINE_OF_SIGHT = 200
CREATURE_BODY = [
    [(0, 0, CREATURE_REACH, CREATURE_REACH)],
    [(0, 0, 25, 25)]
]

# Food
FOOD_SCALE = 0.075
FOOD_SIZE = 50
FOOD_BODY = [
    [(0, 0, FOOD_SIZE, FOOD_SIZE)]
]
