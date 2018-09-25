# dna.py
# Description: dna object for creature.
# ---------------------------------------------------------------------------------------------------------------------

# Imports
from typing import Dict, Tuple, Type

# Constants
from Constants.constants import DNA_STRING
from Constants.types import NodeObject
# Objects
from connection import Connection
from functions import dict_string
from node import InputNode, HiddenNode, OutputNode


class Dna:

    def __init__(self, inputs: int = None, outputs: int = None, weight_range: float = 2.0,
                 nodes: Dict[int, NodeObject] = None,
                 connections: Dict[int, Connection] = None):

        # Take input & output node amount if given, else take values.
        self.inputs = len([node for node in nodes if isinstance(node, InputNode)]) \
            if nodes else inputs
        self.outputs = len([node for node in nodes if isinstance(node, OutputNode)]) \
            if nodes else outputs
        self.weight_range = self.bias_range = weight_range

        # Generate nodes if not given any.
        self.nodes = nodes if nodes is not None else self.generate_nodes()
        self.input_nodes = self.get_node_by_type(InputNode)
        self.output_nodes = self.get_node_by_type(OutputNode)

        # Generate connections if not given any.
        self.connections = connections if connections is not None else self.connect_nodes()
        self.node_connections = {node: self.get_node_connections(node) for node in self.nodes.values()}

    def __str__(self):
        return DNA_STRING.format(len(self.input_nodes), len(self.get_node_by_type(HiddenNode)), len(self.output_nodes),
                                  dict_string(self.node_connections))

    def __repr__(self):
        return str(self)

    def generate_nodes(self) -> Dict[int, NodeObject]:
        """
        Generates input and output nodes.
        """

        nodes = []
        for n in range(self.inputs):
            nodes.append(InputNode(len(nodes)))
        for n in range(self.outputs):
            nodes.append(OutputNode(len(nodes), self.bias_range))

        return {node.number: node for node in nodes}

    def get_node_by_type(self, node_type: Type[NodeObject]) -> Tuple[NodeObject]:
        """
        Finds all nodes of type node_type.
        """

        # Use type(x) is y, since we want exact types, ignoring inheritance.
        return tuple(node for node in self.nodes.values() if type(node) is node_type)

    def connect_nodes(self) -> Dict[int, Connection]:
        """
        Fully connects all input nodes to output nodes.
        :return: Dict of indexes corresponding with connections.
        """

        connections = []
        for src in self.input_nodes:
            for dst in self.output_nodes:
                connections.append(Connection(len(connections), src.number, dst.number, self.weight_range))

        return {connection.number: connection for connection in connections}

    def get_node_connections(self, node: NodeObject) -> Dict[str, Tuple[Connection]]:
        """
        Returns all connections from node and into node (src, dst).
        :param node: Node object.
        """
        src = tuple(connection for connection in self.connections.values() if connection.src_number == node.number)
        dst = tuple(connection for connection in self.connections.values() if connection.dst_number == node.number)

        return {'src': src, 'dst': dst}


if __name__ == '__main__':
    n = Dna(2, 1, 2)
    print(n)
    print(n.get_node_by_type(InputNode))
