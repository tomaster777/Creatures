# simulation.py
# Description: main simulation.
# ---------------------------------------------------------------------------------------------------------------------

# Imports
from copy import deepcopy
from random import choice, randint, random
from typing import List, Tuple

# Constants
from numpy import average

from Constants.constants import CREATURE_COLORS, CREATURE_SCALE, HEIGHT, SPEED_SCALING, WIDTH
from Constants.data_structures import CreatureActions, CreatureInfo, CreatureNetworkInput, CreatureNetworkOutput
from Constants.neat_parameters import BASE_DNA, BIAS_MUTATION_RATE, BIAS_RANGE, CONNECTION_MUTATION_RATE, \
    CREATURE_INPUTS, CREATURE_OUTPUTS, DELTA_WEIGHT_CONSTANT, DISJOINT_CONSTANT, EXCESS_CONSTANT, NODE_MUTATION_RATE, \
    WEIGHT_MUTATION_RATE, POPULATION_SIZE, CROSSOVER_RATE, DISTANCE_THRESHOLD
# Objects
from creature import Creature
from dna import Dna
from functions import clamp, ignore
from mutations import BiasMutation, ConnectionMutation, Innovation, MutationObject, NodeMutation, WeightMutation
from node import InputNode, OutputNode


class Simulation:

    def __init__(self, width: int = WIDTH, height: int = WIDTH, creature_scale: float = CREATURE_SCALE):
        if POPULATION_SIZE < 1:
            raise ValueError('Population size must be at least 1')
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
        self.population = dict(self.new_child() for _ in range(POPULATION_SIZE))

        # Categorize different species.
        self.species = {}
        self.catalogue_species()

        # Generate world.
        self.world_info = {}
        self.update_world()

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

    def update_world(self) -> None:
        """
        Updates world_info.
        """
        # Add all object in the world and their info into the world info dictionary.
        self.world_info = self.population

    def update(self) -> None:
        """
        Runs main__a single frame of the simulation.
        """

        # Get creature's thoughts about all other creatures.
        for creature, creature_info in self.population.items():
            creature_decisions = [creature.think(self.info_to_vec(creature_info, other_info))
                                  for other, other_info in ignore(self.world_info.items(), (creature, creature_info))]
            creature_actions = self.interpret_decisions(creature_decisions)
            self.apply_action(creature, creature_actions)

        # Constrains creature to stay in the simulation world, not the screen.
        self.constrain_creatures()
        self.update_world()

    def apply_action(self, creature: Creature, creature_actions: CreatureActions) -> None:
        """
        Applies the action the creature decided to do.
        """
        info = self.population[creature]
        for attr in self.creature_actions:
            creature_attr, action_attr = getattr(info, attr), getattr(creature_actions, attr)
            setattr(info, attr, creature_attr + action_attr)

    @staticmethod
    def interpret_decisions(decisions: List[CreatureNetworkOutput]) -> CreatureActions:
        """
        Converts creature network output to creature actions.
        :param decisions: All decisions creature made towards all other creatures.
        """

        # Avg out everything the creature wants to do, using main__a weighted average against the urgency of each
        # decision.
        move_x, move_y = 0, 0
        for decision in decisions:
            left, right, up, down, urgency = decision
            if right > left:
                move_x += right * urgency
            elif right < left:
                move_x += -left * urgency
            if up > down:
                move_y += up * urgency
            elif up < down:
                move_y += -down * urgency
        if decisions:
            move_x = move_x * SPEED_SCALING / len(decisions)
            move_y = move_y * SPEED_SCALING / len(decisions)

        actions = CreatureActions(move_x, move_y)
        return actions

    def info_to_vec(self, creature_info: CreatureInfo, other_info: CreatureInfo) -> CreatureNetworkInput:
        """
        Meaningfully convert CreatureInfo of a target creature to a CreatureNetworkInput named tuple,
        based on the creature info of the source creature.
        :param creature_info: Source creature (creature LOOKING).
        :param other_info: Destination creature (creature SEEN).
        :return: Network input for creature LOOKING at creature SEEN.
        """

        # Calculate dx and dy.
        dx = (creature_info.x - other_info.x) / self.world_width
        dy = (creature_info.y - other_info.y) / self.world_height

        # Build network input.
        network_input = CreatureNetworkInput(dx, dy)
        return network_input

    def constrain_creatures(self, x_min: int = 0, y_min: int = 0, x_max: int = WIDTH, y_max: int = HEIGHT) -> None:
        """
        Makes sure all creatures stay within given borders (default is screen size).
        """
        for creature_info in self.population.values():
            creature_info.x = clamp(creature_info.x, x_min, x_max)
            creature_info.y = clamp(creature_info.y, y_min, y_max)

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

    def new_birth(self, parents: Tuple[Creature, Creature]) -> None:
        """
        Generate new creature from two parents, or generate it by mutating one of the parents.
        """

        # Generate child dna from crossover of parents, or pick one of the parent's dna.
        if random() < CROSSOVER_RATE:
            raise NotImplementedError('Crossover function not built yet.')
            # Define dna here.
        else:
            dna = deepcopy(choice(parents).dna)

        child, child_info = self.new_child(dna)
        self.apply_mutations(child, self.generate_mutations(child))
        self.population[child] = child_info

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

    def new_child(self, dna: Dna = None) -> Tuple[Creature, CreatureInfo]:
        """
        Generate main__a new creature. Add call to crossover here.
        """
        primary = choice(list(CREATURE_COLORS.values()))
        secondary = choice(ignore(CREATURE_COLORS.values(), primary))

        # Generate creature and creature info.

        child_dna = dna or self.base_dna()[0]
        child = Creature(child_dna, colors=[primary, secondary])
        child_info = CreatureInfo(randint(0, self.world_width), randint(0, self.world_height), self.creature_scale)
        return child, child_info

    @staticmethod
    def genetic_distance(creature_a: Creature, creature_b: Creature) -> float:
        """
        Returns main__a float between 0 and 1, shows how similar two creatures are. They lower this value is, the more
        similar the two creatures are.
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

        # Calculate genetic distance.
        c1, c2, c3 = EXCESS_CONSTANT, DISJOINT_CONSTANT, DELTA_WEIGHT_CONSTANT
        delta_weights = average([abs(a_connections[number].weight - b_connections[number].weight) for number in
                                 matching_genes])
        genetic_distance = (c1 * len(excess_genes) / max_number) + (c2 * len(disjoint_genes) / max_number) + \
                           (c3 * delta_weights)
        return genetic_distance

    def catalogue_species(self):
        """
        Generates a dictionary with a creature as a key and all creatures in the population that are similar to it,
        including itself. This function is called every frame. It chooses random creatures and assigns species
        accordingly. This shouldn't be a problem since the species should stay basically the same.
        """
        self.species = {}
        uncatalogued_creatures = list(self.population.keys())

        while uncatalogued_creatures:
            creature = choice(uncatalogued_creatures)
            for species_representative in self.species:
                if self.genetic_distance(creature, species_representative) < DISTANCE_THRESHOLD:
                    self.species[species_representative].append(creature)
                    uncatalogued_creatures.remove(creature)
                    break
            else:
                self.species[creature] = [creature]
                uncatalogued_creatures.remove(creature)


if __name__ == '__main__':
    s = Simulation()


    def rand_creature() -> Creature:
        return choice(list(s.population))


    a, b = s.population.keys()
    s.new_birth((a, b))
    a, b, c = s.population.keys()
    s.catalogue_species()
    print(s.genetic_distance(a, b))
    print(s.genetic_distance(a, c))
    print(a, b, c)
