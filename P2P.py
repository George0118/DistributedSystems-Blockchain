import socket
import threading
import time
import pickle

# Class for the bootstrapping and "node-discovery" (represents all nodes' process, including bootstrap's)
class P2P:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.connections = []
        self.peers = []
        self.bootstrap_node = ("127.0.0.1", 40000)
        self.cluster_size = 3

        self.p2p_network_init()
        self.blockchaining()

    # Method to connect to a peer and share with it the listening address (port)
    def connecting(self, peer_address):
        peer_ip, peer_port = peer_address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            connection = self.socket.connect((peer_ip, peer_port))
            self.connections.append(self.socket)
            self.peers.append(peer_address)
            print(f"  |-> Connected to {peer_ip}:{peer_port}")

            self.socket.sendall(pickle.dumps((self.ip, self.port)))
        except socket.error as e:
            print(f"Failed to connect to {peer_ip}:{peer_port}. Error: {e}")            

    # Method for sending messages-data
    def data_exchange(self, data):
        for connection in self.connections:
            try:
                connection.sendall(pickle.dumps(data))
            except socket.error as e:
                print(f"Failed to send data. Error: {e}")

    # Method to listen for upcoming connections and receive address to append to peers' addresses list
    # The bootstrap-node, additionally, sends so-far-peers' addresses' list
    def listening_for_connections(self):
        print(f"Listening for connections on {self.ip}:{self.port}")
        while (len(self.connections) < self.cluster_size - 1):
            connection, address = self.listening_socket.accept()
            self.connections.append(connection)

            listening_address = pickle.loads(connection.recv(1024))
            print(f"Accepted connection from {listening_address}")

            if (self.port == 40000):
                self.data_exchange(self.peers)
            self.peers.append(listening_address)


    def p2p_network_init(self):
        # Listening socket, bound to the address (ip, port) of the peer
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # AF_INET: IPv4, SOCK_STREAM: TCP
        self.listening_socket.bind((self.ip, self.port))
        self.listening_socket.listen(10)    # 10: "concurrent connection attempts" - queue size

        # Bootstrap-node process: Listening to connections and sharing so-far-cluster-state
        if (self.port == 40000):
            self.listening_for_connections()

        # Non-bootstrap-node process: Connecting to the bootstrap-node, acquiring addresses of 
        #                             already-connected nodes, atttempting to connect with those and
        #                             start listening for future connections (until reaching targeted cluster size)
        else:
            self.connecting(self.bootstrap_node)
            peer_addresses = pickle.loads(self.socket.recv(1024))
            print(f"Received addresses (ip, port): ", peer_addresses)

            print("Initialising connections with the above addresses")
            for address in peer_addresses:
                self.connecting(address)

            self.listening_for_connections()

        print("End of bootstraping phase!")


    def listening():
        print(f"Listening on {self.ip}:{self.port}")
        while True:


    def blockchaining(self):
        ## Next: Threading for two functions: listen(), to listen for messages
        ##       and message(), to send a message at the client's (keyboard's) request

## Detailsthat may be important later on: dictionary for the connections and the addresses
## to include names (node 1, node 2, etc.)
