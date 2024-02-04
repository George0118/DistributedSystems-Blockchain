"""To allow P2P communication with other nodes"""

import json
from p2pnetwork.node import Node
from peer_discovery_handler import PeerDiscoveryHandler
from socket_connector import SocketConnector
from blockchain_utils import BlockChainUtils
import setup_parameters


class SocketCommunication(Node):
    """To allow P2P communication with other nodes"""

    def __init__(self, ip, port):
        super(SocketCommunication, self).__init__(ip, port, None)
        self.peers = []  # List of connected nodes
        self.peer_discovery_handler = PeerDiscoveryHandler(
            self
        )  # Creates peer discovery handler
        self.socket_connector = SocketConnector(ip, port)
        self.node = None

    def connect_to_first_node(self):
        """Creates connection with very first node"""
        if (
            self.socket_connector.port != setup_parameters.DEFAULT_NODE_PORT
            and self.socket_connector.ip != setup_parameters.DEFAULT_NODE_IP
        ):

            self.connect_with_node(
                setup_parameters.DEFAULT_NODE_IP, setup_parameters.DEFAULT_NODE_PORT
            )

    def start_socket_communication(self, node):
        """Uses provided IP and port (which form a socket) to open communication
        with other nodes"""
        self.node = node
        self.start()
        self.peer_discovery_handler.start()
        self.connect_to_first_node()

    def inbound_node_connected(self, node):
        """Performs 'handshake' when node connects to you"""
        self.peer_discovery_handler.handshake(node)

    def outbound_node_connected(self, node):
        """Performs 'handshake' when you connect to a node"""
        self.peer_discovery_handler.handshake(node)

    def node_message(self, node, data):
        """To send a message to a connected node"""
        message = BlockChainUtils.decode(
            json.dumps(data)
        )  # Decodes message back to object
        if message.messageType == "DISCOVERY":
            self.peer_discovery_handler.handle_message(data)
        elif message.messageType == "TRANSACTION":
            transaction = message.data
            self.node.handleTransaction(transaction)
        elif message.messageType == "BLOCK":
            block = message.data
            self.node.broadcast_block(block)
        elif message.messageType == "BLOCKCHAINREQUEST":
            self.node.handleBlockchainRequest(node)
        elif message.messageType == "BLOCKCHAIN":
            blockchain = message.data
            self.node.handleBlockchain(blockchain)

    def send(self, receiver, message):
        """Sends message to specific node"""
        self.send_to_node(receiver, message)

    def broadcast(self, message):
        """Broadcasts message to all connected nodes"""
        self.send_to_nodes(message)
