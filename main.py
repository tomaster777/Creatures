# main.py
# Description: project constants.
# ---------------------------------------------------------------------------------------------------------------------


import sys

from graphics import Graphics
from simulation import Simulation
from neat_parameters import POPULATION_SIZE, CREATURE_INPUTS, CREATURE_OUTPUTS
from Constants.constants import WIDTH, HEIGHT, CAPTION

# Run simulation.
if __name__ == '__main__':
    simulation = Simulation(POPULATION_SIZE, CREATURE_INPUTS, CREATURE_OUTPUTS)
    creature1, creature2 = simulation.population.keys()
    c1, c2 = simulation.population.values()
    temp1 = simulation.info_to_vec(c1, c2)
    temp2 = simulation.info_to_vec(c2, c1)
    graphics = Graphics(simulation, WIDTH, HEIGHT, CAPTION)
    graphics.run()
    sys.exit(1)










