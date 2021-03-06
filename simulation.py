# simulation.py
# Description: main simulation.
# ---------------------------------------------------------------------------------------------------------------------

# Imports
import time
from copy import deepcopy
from random import choice, randint, random
from typing import Dict, List, Tuple, Iterator

import numpy as np
from numpy import average, math

# Constants
from Constants.constants import CREATURE_COLORS, CREATURE_SCALE, DEBUG, FOOD_SCALE, FOOD_SIZE, SIMULATION_HEIGHT, \
    SIMULATION_WIDTH, SPEED_SCALING, FOOD_TIME_START, TEXT_ONLY, SIMULATION_REPORT, PRINT_FREQUENCY
from Constants.data_structures import CreatureActions, CreatureNetworkInput, CreatureNetworkOutput, \
    Location
from Constants.neat_parameters import BASE_DNA, BIAS_MUTATION_RATE, BIAS_RANGE, BIG_SPECIES, BOTTOM_PERCENT, \
    CONNECTION_MUTATION_RATE, CREATURE_INPUTS, CREATURE_OUTPUTS, CROSSOVER_RATE, DELTA_WEIGHT_CONSTANT, \
    DISJOINT_CONSTANT, DISTANCE_THRESHOLD, EXCESS_CONSTANT, INTER_SPECIES_MATE, MAX_AGE, MAX_FOOD_AMOUNT, NEW_CHILDREN, \
    NODE_MUTATION_RATE, POPULATION_SIZE, WEIGHT_MUTATION_RATE, MATING_URGE_THRESHOLD
# Objects
from creature import Creature
from dna import Dna
from food import Food
from functions import append_dict, clamp, euclidian_distance, flatten, ignore, sum_one, wrap
from mutations import BiasMutation, ConnectionMutation, Innovation, MutationObject, NodeMutation, WeightMutation
from node import InputNode, OutputNode


class Simulation:

    def __init__(self, population_size: int = POPULATION_SIZE, width: int = SIMULATION_WIDTH, height: int = SIMULATION_WIDTH,
                 creature_scale: float = CREATURE_SCALE):
        self.generation_time = MAX_AGE
        self.generation = 1
        self.simulation_time = 1
        self.colors = self.new_color()
        if population_size < 1:
            raise ValueError('Population size must be at least 1')

        self.current_best = 0
        self.population_size = population_size
        self.world_width = width
        self.world_height = height
        self.creature_scale = creature_scale
        self.innovation_history = []

        # All attributes that can be changed in creature info.
        self.creature_actions = 'x', 'y'

        # Define genotype that starts evolution, and set innovation history, connection and node count accordingly.
        base_dna, self.innovation_history = self.base_dna()
        self.connection_count = len(self.innovation_history) + 1
        self.node_count = len(base_dna.nodes) + 1

        # Map creatures to creature info named tuples.
        self.population = dict(self.initialize_child() for _ in range(self.population_size))

        # Categorize different species.
        self.species = {}
        self.update_species()

        # Creatures scheduled to die.
        self.dead_creatures = []

        # Generate food.
        self.foods = {}
        self.new_food(population_size)

        # Generate world.
        self.world_info = {}
        self.update_world()

        if TEXT_ONLY:
            self.report = SIMULATION_REPORT

    def update_world(self) -> None:
        """
        Updates world_info.
        """
        # Add all object in the world and their info into the world info dictionary.
        self.world_info = append_dict(self.population, self.foods)

    def update(self) -> None:
        """
        Runs a single frame of the simulation.
        """
        self.simulation_time += 1

        if self.simulation_time % PRINT_FREQUENCY == 0 and TEXT_ONLY:
            print(self.report.format(self.generation, self.simulation_time, len(self.population), len(self.species),
                                     self.current_best))

        # Get creature's thoughts about all other creatures.
        for creature, creature_location in self.population.items():
            objects_in_view = [(other, other_info) for other, other_info in
                               ignore(self.world_info.items(), (creature, creature_location))
                               if euclidian_distance(creature_location.x, creature_location.y,
                                                     other_info.x, other_info.y) < creature.line_of_sight]
            creature_decisions = [creature.think(self.info_to_vec(creature_location, other, other_info))
                                  for other, other_info in objects_in_view]
            creature_actions = self.interpret_decisions(list(zip(objects_in_view, creature_decisions)))
            self.apply_action(creature, creature_location, creature_actions)

            # Add fitness to creature based on his actions.
            # Add 1 for each frame creature is alive.
            self.update_creature_properties(creature, creature_actions)

            # Check if creature ate a food.
            # Food can only be eaten after 30 seconds of simulation, to avoid spawn eating.
            if self.simulation_time > FOOD_TIME_START:
                for food, food_location in self.foods.items():
                    distance = euclidian_distance(food_location.x, food_location.y, creature_location.x,
                                                  creature_location.y)
                    distance -= food.amount * FOOD_SIZE * food_location.scale
                    if distance < creature.reach * creature_location.scale:
                        self.creature_eat(creature, food)

        # Kill creatures that died.
        self.kill_creatures()

        # Simulate a round world for the creatures.
        self.wrap_creatures()
        self.update_world()

        # Find the best creature.
        self.current_best = max(self.population, key=lambda c: c.fitness).fitness

    def apply_action(self, creature: Creature, creature_location: Location, creature_actions: CreatureActions) -> None:
        """
        Applies the action the creature decided to do.
        """
        for attr in self.creature_actions:
            creature_attr, action_attr = getattr(creature_location, attr), getattr(creature_actions, attr)
            setattr(creature_location, attr, creature_attr + action_attr)

    def info_to_vec(self, creature_info: Location, other, other_info: Location) -> CreatureNetworkInput:
        """
        Meaningfully convert CreatureInfo of a target creature to a CreatureNetworkInput named tuple,
        based on the creature info of the source creature.
        :param creature_info: Source creature (creature LOOKING).
        :param other_info: Destination creature (creature SEEN).
        :return: Network input for creature LOOKING at creature SEEN.
        """
        if isinstance(other_info, Location):
            # Calculate dx and dy.
            dx = (creature_info.x - other_info.x) / self.world_width
            dy = (creature_info.y - other_info.y) / self.world_height
            type = int(isinstance(other, Food))

            # Build network input.
            network_input = CreatureNetworkInput(dx, dy, type)
            return network_input
        else:
            raise NotImplementedError("Creatures can only 'see' other creatures and foods")

    def constrain_creatures(self, x_min: int = 0, y_min: int = 0, x_max: int = SIMULATION_WIDTH,
                            y_max: int = SIMULATION_HEIGHT) -> None:
        """
        Makes sure all creatures stay within given borders (default is screen size).
        """
        for creature_info in self.population.values():
            creature_info.x = clamp(creature_info.x, x_min, x_max)
            creature_info.y = clamp(creature_info.y, y_min, y_max)

    def wrap_creatures(self, x_min: int = 0, y_min: int = 0, x_max: int = SIMULATION_WIDTH,
                       y_max: int = SIMULATION_HEIGHT) -> None:
        """
        Simulates a round world.
        """
        for creature_info in self.population.values():
            creature_info.x = wrap(creature_info.x, x_min, x_max)
            creature_info.y = wrap(creature_info.y, y_min, y_max)

    @staticmethod
    def weight_mutation(creature: Creature) -> WeightMutation:
        """
        Return main__a weight mutation object from the creature. A weight mutation has no number, the object is here
        for organization purposes. ALWAYS returns main__a mutation, random chance is handle in simulation.mutate().
        """

        # Choose random connection.
        connection = choice(list(creature.dna.connections.values()))

        # Generate random weight mutation.
        mutation = WeightMutation(connection)
        return mutation

    @staticmethod
    def bias_mutation(creature: Creature) -> BiasMutation:
        """
        Return main__a weight mutation object from the creature. A weight mutation has no number, the object is here
        for organization purposes. ALWAYS returns main__a mutation, random chance is handle in simulation.mutate().
        """

        # Choose random node.
        node = choice(list(creature.dna.nodes.values()))

        # Generate random weight mutation.
        mutation = BiasMutation(node)
        return mutation

    @staticmethod
    def connection_mutation(creature: Creature) -> ConnectionMutation:
        """
        Returns main__a new old_connection mutation based on the creature.
        """

        # Get all creature dna's nodes and connections.
        available_connections = creature.dna.available_connections()

        # Choose random connection to generate.
        src, dst = choice(available_connections)

        # Generate new connection between nodes.
        mutation = ConnectionMutation(None, src, dst)
        return mutation

    @staticmethod
    def node_mutation(creature: Creature) -> NodeMutation:
        """
        Returns main__a new node mutation based on the creature.
        """

        # Choose main__a random connection to split.
        connection = choice(list(creature.dna.connections.values()))

        # Generate node mutation.
        mutation = NodeMutation(connection)
        return mutation

    def mutate(self, creature: Creature) -> List[MutationObject]:
        """
        Get mutations based on the creature, based on random chance and neat_parameter values.
        """
        mutations = []

        # Weight and bias mutations.
        if random() < WEIGHT_MUTATION_RATE and creature.dna.connections:
            mutations.append(self.weight_mutation(creature))
        if random() < BIAS_MUTATION_RATE and creature.dna.nodes:
            mutations.append(self.bias_mutation(creature))

        # Check if main__a connection is possible if random wants to mutate main__a connection.
        if creature.dna.available_connections(shallow=True) and random() < CONNECTION_MUTATION_RATE:
            mutations.append(self.connection_mutation(creature))

        # Node mutation.
        if random() < NODE_MUTATION_RATE and creature.dna.connections:
            mutations.append(self.node_mutation(creature))

        return mutations

    @staticmethod
    def apply_mutations(creature: Creature, mutations: List[MutationObject]) -> None:
        """
        Applies mutation to creature's dna.
        """
        creature.update(mutations)

    def generate_mutations(self, creature: Creature) -> List[MutationObject]:
        """
        Generates mutations for all new creatures, and configures them.
        :return: All mutations for each creature.
        """

        # Generate innovations.
        mutations = self.mutate(creature)
        innovations = [mutation for mutation in mutations if isinstance(mutation, Innovation)]

        # Configure innovations.
        for innovation in innovations:
            for past_innovation in self.innovation_history:
                if innovation.unique() == past_innovation.unique():
                    innovation.configure(*past_innovation.configurations())
                    break
            # If no innovations were matching in past innovations, increment connection and node count.
            # And add innovation to innovation history.
            else:
                self.connection_count, self.node_count = innovation.calc_configurations(self.connection_count,
                                                                                        self.node_count)
                self.innovation_history.append(innovation)
        return mutations

    def add_child(self, child: Creature, child_info: Location) -> None:
        """
        Adds a child to the population
        """
        self.population[child] = child_info

        # Assign the child to a species.
        self.catalogue_creature(child)

    def new_birth(self, parents: Tuple[Creature, Creature]) -> Tuple[Creature, Location]:
        """
        Generate new creature from two parents, or generate it by mutating one of the parents.
        """

        # Generate child dna from crossover of parents, or pick one of the parent's dna.
        if random() < CROSSOVER_RATE:
            dna = self.crossover(*parents)
        else:
            dna = deepcopy(choice(parents).dna)

        child, child_info = self.initialize_child(dna, parents)
        self.apply_mutations(child, self.generate_mutations(child))

        return child, child_info

    def initialize_child(self, dna: Dna = None, parents: Tuple[Creature, Creature] = None) -> Tuple[Creature, Location]:
        """
        Initializes creature in the world.
        """
        primary = choice(list(CREATURE_COLORS.values()))
        secondary = choice(ignore(CREATURE_COLORS.values(), primary))

        # Generate creature and creature info.
        child_dna = dna or self.base_dna()[0]
        child = Creature(child_dna, colors=[primary, secondary])
        if parents:
            a, b = parents
            a_info, b_info = self.population[a], self.population[b]
            child_info = Location((a_info.x + b_info.x) / 2, (a_info.y + b_info.y) / 2, self.creature_scale)
        else:
            child_info = Location(randint(0, self.world_width), randint(0, self.world_height), self.creature_scale)

        return child, child_info

    def get_species(self, creature: Creature) -> Creature:
        """
        Returns the species representative of creature.
        """
        for rep, species in self.species.items():
            if creature in species:
                return rep
        raise Exception("Shouldn't be reachable")

    def crossover(self, parent_a: Creature, parent_b: Creature) -> Dna:
        """
        Generates a new child with crossover.
        """

        # Compare both parent's genes.
        matching, disjoint, excess, max_number, a_connections, b_connections = self.compare_genomes(parent_a, parent_b)
        fit_parent = parent_a if parent_a.fitness > parent_b.fitness else parent_b \
            if parent_a.fitness < parent_b.fitness else None
        non_matching = disjoint + excess

        # Decide which genes the child will inherit.
        # For each gene, add the parent it will be inherited from. After everything is decided add the genes.
        child_gene_sources = dict()
        for number in matching:

            # Inherit weight from a random parent.
            if random() < 0.5:
                child_gene_sources[number] = parent_a
            else:
                child_gene_sources[number] = parent_b

        # If there is a fit parent, inherit disjoint and matching genes from it.
        if fit_parent:
            for number in non_matching:
                if number in fit_parent.dna.connections:
                    child_gene_sources[number] = fit_parent

        # If both parents are equally fit, inherit disjoint and excess genes randomly.
        else:
            for number in non_matching:
                if random() < 0.5 and number in a_connections:
                    child_gene_sources[number] = parent_a
                elif number in b_connections:
                    child_gene_sources[number] = parent_b

        # Add all genes the child should inherit.
        child_connections = dict()
        child_nodes = dict()
        for number, parent in child_gene_sources.items():
            connection = parent.dna.connections[number]
            child_connections[number] = connection
            src_number, dst_number = connection.src_number, connection.dst_number
            child_nodes[src_number] = parent.dna.nodes[src_number]
            child_nodes[dst_number] = parent.dna.nodes[dst_number]

        # Generate child.
        child_dna = Dna(nodes=child_nodes, connections=child_connections)
        return child_dna

    def creature_death(self, creature: Creature) -> None:
        """
        Handles the death of a creature.

        Removes the creature from the population dictionary and generates a new child in its place.
        Calls add_child, new_birth.
        """

        # Choose parents.
        parent_a, parent_b = self.get_parents()

        # Birth new child, to replace dead creature.
        self.add_child(*self.new_birth((parent_a, parent_b)))

        # Kill creature
        del self.population[creature]
        self.species[self.get_species(creature)].remove(creature)

    def catalogue_creature(self, creature: Creature) -> None:
        """
        Checks if the creature fits any of the existing species, if not, generates a new species.
        """
        for species_representative in self.species:
            if self.genetic_distance(creature, species_representative) < DISTANCE_THRESHOLD:
                creature.colors = species_representative.colors
                self.species[species_representative].append(creature)
                break
        else:
            creature.colors = next(self.colors)
            self.species[creature] = [creature]

    @staticmethod
    def compare_genomes(creature_a: Creature, creature_b: Creature):
        """"
        Generate matching, disjoint and excess gene lists for two creature's dna.
        """
        # Get both creatures connection genes. Reminder: Connections is main__a dict => {innovation number: connection}
        a_connections = creature_a.dna.connections
        b_connections = creature_b.dna.connections

        # Check which creature has the latest innovation.
        a_max = max(a_connections.keys())
        b_max = max(b_connections.keys())

        # Calculate disjoint-excess cutoff.
        cutoff = min(a_max, b_max)
        max_number = max(a_max, b_max)

        # Get matching, disjoint and excess genes.
        matching_genes = []
        disjoint_genes = []
        excess_genes = []

        # Line up corresponding mutations by number.
        a_compare = [None if num not in a_connections else a_connections[num].number for num in range(max_number + 1)]
        b_compare = [None if num not in b_connections else b_connections[num].number for num in range(max_number + 1)]
        for a_num, b_num in zip(a_compare, b_compare):

            # Matching genes.
            if a_num == b_num and a_num:
                matching_genes.append(a_num)

            # Disjoint genes.
            elif (a_num or b_num) and (a_num or b_num) < cutoff:
                disjoint_genes.append(a_num or b_num)

            # Excess genes.
            elif a_num or b_num:
                excess_genes.append(a_num or b_num)
        return matching_genes, disjoint_genes, excess_genes, max_number, a_connections, b_connections

    def genetic_distance(self, creature_a: Creature, creature_b: Creature) -> float:
        """
        Returns main__a float between 0 and 1, shows how similar two creatures are. They lower this value is, the more
        similar the two creatures are.
        """
        matching_genes, disjoint_genes, excess_genes, max_number, a_connections, b_connections = self.compare_genomes \
            (creature_a, creature_b)

        # Calculate genetic distance.
        c1, c2, c3 = EXCESS_CONSTANT, DISJOINT_CONSTANT, DELTA_WEIGHT_CONSTANT
        delta_weights = average([abs(a_connections[number].weight - b_connections[number].weight) for number in
                                 matching_genes])
        genetic_distance = (c1 * len(excess_genes) / max_number) + (c2 * len(disjoint_genes) / max_number) + \
                           (c3 * delta_weights)
        return genetic_distance

    def update_species(self, new_creature: Creature = None) -> None:
        """
        Generates a dictionary with a creature as a key and all creatures in the population that are similar to it,
        including itself. This function is called every time a creature is born. The creature representing a species
        can die, but it will still represent that species until the SPECIES dies.
        """

        # Check genetic distance from all species representatives, if it is smaller than the threshold catalogue the,
        # creature into that species. If no matching species was found then make a new one with creature as the rep.
        if new_creature is None:

            # Find all creatures not catalogued into a species.
            all_creatures = flatten(list(self.species.values()))
            uncatalogued_creatures = [creature for creature in self.population if creature not in all_creatures]
        else:

            # Can save time if new creature is specified
            uncatalogued_creatures = [new_creature]

        while uncatalogued_creatures:
            creature = choice(uncatalogued_creatures)
            self.catalogue_creature(creature)
            uncatalogued_creatures.remove(creature)

    def update_creature_properties(self, creature: Creature, creature_actions: CreatureActions) -> None:
        """
        Updates the creature properties according to its actions.
        """

        # The more the creature moves, the higher its fitness.
        distance = math.sqrt(math.pow(creature_actions.x, 2) + math.pow(creature_actions.y, 2))
        creature.fitness += distance
        creature.distance_travelled += distance
        creature.age += 1
        if int(creature.distance_travelled) % 30 == 0:
            creature.age -= 5
        if creature.age >= MAX_AGE:
            self.dead_creatures.append(creature)

    def get_parents(self) -> Tuple[Creature, Creature]:
        """
        Returns two parents to generate a new child, based on creature and species fitness.
        In the future the creatures should learn how to do this.
        """

        # Adjust fitness levels based on explicit fitness sharing.
        fitness_levels = dict()
        for rep, species in self.species.items():
            fitness_levels[rep] = dict()

            # Each creatures fitness is divided by the amount of creatures in its species.
            for creature in species:
                fitness_levels[rep][creature] = creature.fitness / len(species)

        # Choose a species.
        # TODO 10/22/18 get_parents: Use numpy weighted choice.
        a_species = choice(list(self.species.keys()))

        # Choose the first parent from the species chosen.
        # Choose the second one from the same species, unless inter-species mating occurs.
        b_species = choice(ignore(list(self.species.keys()), a_species)) if random() < INTER_SPECIES_MATE else a_species

        # Return parents.
        parent_a = choice(self.species[a_species])
        parent_b = choice(ignore(self.species[b_species], parent_a))
        return parent_a, parent_b

    def new_generation(self) -> Dict[Creature, Location]:
        """
        Generates a new generation based on the fitness levels of each creature and each species.
        """

        # Kill bottom percent of each species.
        survivors = dict(self.species)
        for rep, species in survivors.items():
            survivors[rep] = sorted(species, key=lambda c: c.fitness)[int(len(species) * BOTTOM_PERCENT):]

        species_fitness = dict()

        # Adjust fitness levels based on explicit fitness sharing.
        fitness_levels = dict()
        for rep, species in survivors.items():
            fitness_levels[rep] = dict()

            # Each creatures fitness is divided by the amount of creatures in its species.
            for creature in species:
                fitness_levels[rep][creature] = creature.fitness / len(species)

        # The fitness of a species is the sum of all the adjusted fitness levels of its creatures.
        for rep, species in survivors.items():
            species_fitness[rep] = sum([fitness_levels[rep][creature] for creature in species])

        # Generate new generation using survivors as parents.
        new_generation = dict()
        for rep, species in survivors.items():
            new_species = []

            # Species with more than BIG SPECIES amount of networks keep their champion.
            if len(new_species) > BIG_SPECIES:
                champion = max(species, key=lambda c: c.fitness)
                new_species.append(champion)
            for i in range(len(species) + NEW_CHILDREN):
                parent_b_species = rep

                # Choose parent a.
                parent_a_probabilities = sum_one(list(fitness_levels[rep].values()))
                parent_a = np.random.choice(species, p=parent_a_probabilities)
                species_p = sum_one(species_fitness.values())
                if random() < INTER_SPECIES_MATE:
                    parent_b_species = np.random.choice(survivors, p=species_p)

                # Choose parent b.
                parent_b_options = ignore(survivors[parent_b_species], parent_a)

                # If mate species contains only one creature, it will mate with itself.
                if not parent_b_options:
                    parent_b_options = survivors[parent_b_species]
                parent_b_probabilities = sum_one([fitness_levels[parent_b_species][creature]
                                                  for creature in parent_b_options])
                parent_b = np.random.choice(parent_b_options, p=parent_b_probabilities)
                child, child_info = self.new_birth((parent_a, parent_b))
                new_generation[child] = child_info

        return new_generation

    def new_food(self, total: int, remove: Food = None) -> None:
        """
        Generates total new foods.
        """

        for _ in range(total):
            food = Food(randint(0, self.world_width), randint(0, self.world_height), randint(0, MAX_FOOD_AMOUNT))
            self.foods[food] = Location(food.x, food.y, food.amount * FOOD_SCALE)

        if remove:
            del self.foods[remove]

    def creature_eat(self, creature: Creature, food: Food) -> None:
        """
        Handles a creature eating a piece of food.
        """

        if DEBUG:
            print(creature, "is eating", food)
        creature.health = min(creature.health + 10, 100)
        creature.fitness += 10
        food.amount -= 1
        if food.amount <= 0:
            self.new_food(1, remove=food)

    def kill_creatures(self):
        """
        Kill all creatures in dead creatures array.
        """

        # Make sure there are no duplicates in dead creatures.
        self.dead_creatures = set(self.dead_creatures)
        for creature in self.dead_creatures:
            self.creature_death(creature)

        # Reset dead creatures.
        self.dead_creatures = []

    @staticmethod
    def base_dna() -> Tuple[Dna, List[ConnectionMutation]]:
        """
        Generate base Dna to start creatures from, connect nodes with connection mutations.
        """

        # Generate base Dna to start creatures from.
        base_nodes = {}
        for num in range(1, CREATURE_INPUTS + CREATURE_OUTPUTS + 1):
            base_nodes[num] = InputNode(num) if num < CREATURE_INPUTS + 1 else OutputNode(num, BIAS_RANGE)

        # Connect nodes with connection mutations.
        base_dna = Dna(CREATURE_INPUTS, CREATURE_OUTPUTS, nodes=base_nodes)
        mutations = []

        # Connect nodes by NEAT PARAMETER settings.
        if BASE_DNA == 'CONNECTED':
            for src_number in range(CREATURE_INPUTS):
                for dst_number in range(CREATURE_INPUTS, CREATURE_INPUTS + CREATURE_OUTPUTS):

                    # Generate connection mutation between each Input node to every Output node.
                    mutation = ConnectionMutation(len(mutations) + 1, src_number + 1, dst_number + 1)
                    mutations.append(mutation)
            base_dna.update(mutations)
        return base_dna, mutations

    @staticmethod
    def new_color():
        """
        Generates a new, unused color for a species.
        """
        known_colors = dict()

        # First colors.
        new_p, new_s = choice(list(CREATURE_COLORS.values())), choice(list(CREATURE_COLORS.values()))
        known_colors[new_p] = [new_s]
        done_colors = []
        yield new_p, new_s
        while True:
            new_p = choice(ignore(list(CREATURE_COLORS.values()), done_colors))
            if new_p in known_colors:
                if len(known_colors[new_p]) == len(CREATURE_COLORS) - 2:
                    done_colors.append(new_p)
                new_s = choice(ignore(list(CREATURE_COLORS.values()), known_colors[new_p]))
                known_colors[new_p].append(new_s)
            else:
                known_colors[new_p] = [new_s]

            yield new_p, new_s

    @staticmethod
    def interpret_decisions(decisions: List[Tuple[Tuple[Creature, Location], CreatureNetworkOutput]]) \
            -> CreatureActions:
        """
        Converts creature network output to creature actions.
        :param decisions: All decisions creature made towards all other objects in its line of sight.
        """

        # Avg out everything the creature wants to do, using main__a weighted average against the urgency of each
        # decision.
        move_x, move_y, total = 0, 0, 0
        best_mate, biggest_urge = None, -1
        for (creature, creature_info), decision in decisions:
            left, right, up, down, urgency, mate = decision
            total += 1

            # Mating decision.
            if mate > MATING_URGE_THRESHOLD:
                if urgency > biggest_urge:
                    best_mate = creature
                    biggest_urge = urgency

            # Movement.
            if right > left:
                move_x += right * urgency
            elif right < left:
                move_x += -left * urgency
            if up > down:
                move_y += up * urgency
            elif up < down:
                move_y += -down * urgency

        # Sometimes the creature can't 'see' anything, so total would be 0.
        if total:
            move_x = move_x * SPEED_SCALING / total
            move_y = move_y * SPEED_SCALING / total

        actions = CreatureActions(move_x, move_y, best_mate)
        return actions


if __name__ == '__main__':
    print("Starting Simulation...")
    s = Simulation()
    for _ in range(1000):
        s.update()
    print("Done")

    def rand_creature() -> Creature:
        return choice(list(s.population))
