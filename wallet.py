from config import N, CAPACITY
from Crypto.PublicKey import RSA    # pycryptodome
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import pickle
from transaction import Transaction
from block import Block
from blockchain import Blockchain
from transaction_pool import TransactionPool
from message import Message
import json
from utils import BlockChainUtils
from proof_of_stake import ProofOfStake
import threading

class Wallet:

    def __init__(self):
        self.generate_wallet()
        self.nonce = 0
        self.transaction_pool = TransactionPool()
        self.transaction_pool.set_wallet(self)
        self.pos = ProofOfStake()
        self.await_block = False
        self.lock = threading.RLock()

    def set_peers(self, peers, nodes):
        self.peers = peers
        self.nodes = nodes
        stakes_dict = {}
        self.temp_balance = {}
        for id, dict in self.peers.items():
            stakes_dict[id] = dict["stake"]

        self.fix_temp_balances()

        self.pos.set_stakes(stakes_dict)

        self.id = None
        for id, dict in self.peers.items():
            if dict["public_key"] == self.public_key:
                self.id = id
                break
        self.temp_stake = self.peers[self.id]["stake"]

    def set_blockchain(self, blockchain:Blockchain):
        self.blockchain = blockchain
    
    def generate_wallet(self):
        key = RSA.generate(2048)
        self.private_key = key.export_key().decode('utf-8')
        self.public_key = key.publickey().export_key().decode('utf-8')


    # ============================ TRANSACTION ============================ #
    
    def sign_transaction(self, transaction_data):
        private_key_obj = RSA.import_key(self.private_key)
        transaction_data = json.dumps(transaction_data).encode('utf-8')
        hash_data = SHA256.new(transaction_data)        # transaction_data.encode('utf-8')
        signature = pkcs1_15.new(private_key_obj).sign(hash_data)
        return signature
    
    def verify_transaction(self, public_key, transaction_data, signature):
        public_key_obj = RSA.import_key(public_key)
        transaction_data = json.dumps(transaction_data).encode('utf-8')
        hash_data = SHA256.new(transaction_data)        # transaction_data.encode('utf-8')
        try:
            pkcs1_15.new(public_key_obj).verify(hash_data, signature)
            return True
        except (ValueError, TypeError):
            return False
        

    def create_transaction(self, receiver_address, type, amount, message):
        transaction = Transaction(type, receiver_address, self.public_key, amount, message, self.nonce)
        signature = self.sign_transaction(transaction.payload())
        transaction.transaction_signing(signature)
        self.nonce += 1
        return transaction

    def check_transaction(self, transaction:Transaction):
        """
        Checks if transaction is valid and does not already exist - if valid it broadcasts it
        """
        with self.lock:
            if self.validate_transaction(transaction):
                # If the signature is valid and the transaction is new, it is added to the pool
                self.transaction_pool.add_transaction(transaction)
                self.temp_execute_transaction(transaction)
                return transaction
            else:
                print("Invalid transaction")
                return None
        
    def handle_transaction(self, transaction:Transaction, flag = False):
        """
        Checks if transaction is valid and does not already exist - if valid it broadcasts it
        """
        with self.lock:
            if self.validate_transaction(transaction):
                # If the signature is valid and the transaction is new, it is added to the pool
                self.transaction_pool.add_transaction(transaction)
                self.temp_execute_transaction(transaction)

                if self.transaction_pool.validation_required() and not self.await_block and not flag:
                        block = self.mint_block()
                        if block is not None:
                            self.broadcast_block(block)
            else:
                print("Invalid transaction")

    def validate_transaction(self, transaction:Transaction):
        """
        Validates a transaction
        """
        data = transaction.payload()
        signature = transaction.signature
        signer_address = transaction.sender_address

        signature_valid = self.verify_transaction(signer_address, data, signature)  # Check if signature is valid

        with self.lock:
            transaction_covered = self.transaction_covered(transaction)
            transaction_in_blockchain = self.transaction_in_blockchain(transaction)

        if (
            signature_valid
            and transaction_covered
            and not transaction_in_blockchain
        ):
            return True
        return False     
    
    def transaction_covered(self, transaction:Transaction):
        """ Checks whether the sender has enough money to execute this transaction """
        sender_id = None
        for id, dict_id in self.peers.items():
            if dict_id["public_key"] == transaction.sender_address:
                sender_id = id
        current_balance = self.temp_balance[sender_id]
        if current_balance >= transaction.amount + transaction.fee:
            return True
        else:
            return False
        
    def transaction_in_blockchain(self, transaction:Transaction):
        """ Checks whether a transaction is already in our blockchain """
        for block in self.blockchain.chain:
            for t in block.transactions:
                if transaction.equals(t):
                    return True
        
        return False

        
    def broadcast_transaction(self, transaction: Transaction):
        """ Broadcasts Transaction """
        with self.lock:
            message = Message("TRANSACTION", transaction)
            message = BlockChainUtils.encode(message)

            if message is not None:
                message = pickle.dumps(message)
                for socket in self.nodes.values():
                    socket.sendall(message)
    
    def execute_transaction(self, transaction:Transaction):
        """ Executes a Transaction saving its changes to the wallets"""
        with self.lock:
            # If the transaction is Exchange or Initialization then remove from sender balance and add to receiver
            if transaction.type == "Exchange" or transaction.type == "Initialization":    
                receiver_id = None
                sender_id = None
                for id, dict_id in self.peers.items():
                    if dict_id["public_key"] == transaction.receiver_address:
                        receiver_id = id
                    if dict_id["public_key"] == transaction.sender_address:
                        sender_id = id
                
                self.peers[sender_id]["balance"] -= (transaction.amount + transaction.fee)
                self.peers[receiver_id]["balance"] += transaction.amount

            elif transaction.type == "Stake":       # If the transaction is Stake then remove the money from the balance
                sender_id = None
                for id, dict_id in self.peers.items():
                    if dict_id["public_key"] == transaction.sender_address:
                        sender_id = id
                
                previous_stake = self.peers[sender_id]["stake"]
                
                self.peers[sender_id]["stake"] = transaction.amount

                self.peers[sender_id]["balance"] -= (transaction.amount - previous_stake)

    def temp_execute_transaction(self, transaction:Transaction):
        """ Executes a Transaction saving its changes to the wallets"""
        # If the transaction is Exchange or Initialization then remove from sender balance and add to receiver
        with self.lock:
            if transaction.type == "Exchange" or transaction.type == "Initialization":    
                receiver_id = None
                sender_id = None
                for id, dict_id in self.peers.items():
                    if dict_id["public_key"] == transaction.receiver_address:
                        receiver_id = id
                    if dict_id["public_key"] == transaction.sender_address:
                        sender_id = id
                
                self.temp_balance[sender_id] -= (transaction.amount + transaction.fee)
                self.temp_balance[receiver_id] += transaction.amount

            elif transaction.type == "Stake":       # If the transaction is Stake then remove the money from the balance
                sender_id = None
                for id, dict_id in self.peers.items():
                    if dict_id["public_key"] == transaction.sender_address:
                        sender_id = id

                previous_stake = self.temp_stake
                self.temp_stake = transaction.amount
                self.temp_balance[sender_id] += previous_stake
                self.temp_balance[sender_id] -= transaction.amount

    def initial_distribution(self):
        """ Executes initialization transactions to all peers only from 0 so everyone has 1000 balance """
        for i in range(N):
            if i != 0:
                receiver_address = self.peers['id'+ str(i)]["public_key"]
                transaction = self.create_transaction(receiver_address, "Initialization", 1000, "")

                if self.check_transaction(transaction) is not None:
                    self.broadcast_transaction(transaction)

                if self.transaction_pool.validation_required():
                    block = self.mint_block()
                    if block is not None:
                        self.broadcast_block(block)


    # ========================= BLOCK ========================== #

    def handle_block(self, block:Block):
        """
        Checks if block is valid - if valid it add it to your blockchain
        """
        if self.validate_block(block):
            with self.lock:
                # If block is valid then execute any transactions that are in the block and not in the pool
                for transaction in block.transactions:
                    self.execute_transaction(transaction)

                self.fix_temp_balances()

                self.transaction_pool.remove_from_pool(
                    block.transactions
                )

                # And add the block to the blockchain
                self.stakes_and_messages(block)
                fees = self.blockchain.add_block(block)
                validator_id = None
                for id, dict in self.peers.items():
                    if dict["public_key"] == block.validator:
                        validator_id = id
                        break
                self.peers[validator_id]["balance"] += fees
                self.temp_balance[validator_id] += fees

        else:
            print("Invalid block")
        self.await_block = False

    def validate_block(self, block:Block):
        """
        Validates a block
        """
        # My info
        prev_hash = self.blockchain.get_prevhash()
        validator_id = self.pos.validator(prev_hash)
        validator_pk = self.peers[validator_id]["public_key"]

        # Block info
        block_validator = block.validator
        block_prev_hash = block.previous_hash

        if (
            block_validator == validator_pk
            and block_prev_hash == prev_hash
        ):
            return True
        return False

    def mint_block(self):
        """
        Checks if you are the validator and triggers block creation if necessary
        """
        with self.lock:
            prev_hash = self.blockchain.get_prevhash()
            validator_id = self.pos.validator(prev_hash)
            validator_pk = self.peers[validator_id]["public_key"]
            if validator_pk == self.public_key:
                print("I am the validator")
                index = self.blockchain.next_index()
                block = Block(self.transaction_pool.transactions[:CAPACITY], prev_hash, validator_pk, index)
                for transaction in block.transactions:
                    self.execute_transaction(transaction)

                self.fix_temp_balances()

                self.transaction_pool.remove_from_pool(
                    block.transactions
                )  # Clears transaction pool by removing all transactions added to block

                self.stakes_and_messages(block)
                fees = self.blockchain.add_block(block)
                validator_id = None
                for id, dict in self.peers.items():
                    if dict["public_key"] == block.validator:
                        validator_id = id
                        break
                self.peers[validator_id]["balance"] += fees
                self.temp_balance[validator_id] += fees

                return block
            else:
                print("I am not the validator")
                self.await_block = True
                return None

    def fix_balances(self):
        for id, balance in self.temp_balance.items():
            self.peers[id]["balance"] = balance

    def fix_temp_balances(self):
        with self.lock:
            for id, data in self.peers.items():
                self.temp_balance[id] = data["balance"]

    def stakes_and_messages(self, block: Block):
        with self.lock:
            latest_stakes = {}  # Dictionary to store the latest stake transaction for each node

            for transaction in block.transactions:
                if transaction.type == "Stake":
                    # Get the ID of the node making the stake transaction
                    stake_node_id = None
                    for id, dict_id in self.peers.items():
                        if dict_id["public_key"] == transaction.sender_address:
                            stake_node_id = id
                            break
                    # Update the latest stake transaction for the node
                    if stake_node_id is not None:  # Make sure node ID is found
                        latest_stakes[stake_node_id] = transaction.amount

                if transaction.type == "Exchange" and self.public_key == transaction.receiver_address:
                    sender_id = None
                    for id, dict_id in self.peers.items():
                        if dict_id["public_key"] == transaction.sender_address:
                            sender_id = id
                    if transaction.message != "":
                        print("User with ID", sender_id, "messaged you:", transaction.message)
                    else:
                        print("User with ID", sender_id, "sent you", transaction.amount, "BCCs")

            # Update balances after processing all transactions
            for id, data in self.peers.items():
                # Add the latest stake amount for nodes that have a stake transaction in the block
                if id in latest_stakes:
                    self.temp_balance[id] += data["stake"]
                    self.temp_balance[id] -= latest_stakes[id]

                    # Update the stake amount in the peers dictionary
                    self.peers[id]["stake"] = latest_stakes[id]

            # Update the POS stakes after processing all transactions
            stakes_dict = {}
            for id, data in self.peers.items():
                stakes_dict[id] = data["stake"]
            self.pos.set_stakes(stakes_dict)

    def broadcast_block(self, block:Block):
        """ Broadcasts Block """
        message = Message("BLOCK", block)
        message = BlockChainUtils.encode(message)
        with self.lock:
            if message is not None:
                message = pickle.dumps(message)
                for socket in self.nodes.values():
                    socket.sendall(message)

    def broadcast_blockchain(self, blockchain:Blockchain):
        """ Broadcasts Block """
        message = Message("BLOCKCHAIN", blockchain)
        message = BlockChainUtils.encode(message)

        if message is not None:
            message = pickle.dumps(message)
            for socket in self.nodes.values():
                socket.sendall(message)

    def handle_blockchain(self, blockchain:Blockchain):
        """
        Checks if blockchain is valid - if valid it replaces your blockchain
        """
        if self.validate_blockchain(blockchain):
            self.blockchain = blockchain
        else:
            print("Invalid blockchain")

    def validate_blockchain(self, blockchain:Blockchain):
        """
        Validates a blockchain
        """
        for block in blockchain.chain:
            if block.index == 0:
                continue
            if not self.validate_block(block):
                return False
        return True


    def view_block(self):
        """
        Returns last block's transactions and its validator's id
        """
        last_valid_block = self.blockchain.chain[-1]
        last_block_transactions = last_valid_block.transactions
        last_validator_by_key = last_valid_block.validator
        print("Last validated block's transactions:")
        for transaction in last_block_transactions:
            print(transaction.payload())

        for last_validator_id, data in self.peers.items():
            if data["public_key"] == last_validator_by_key:
                print("With validator (by id): ", last_validator_id)

    def my_balance(self):
        """Returns the balance and safe-state stake of the node"""
        return self.temp_balance[self.id], self.peers[self.id]["stake"]

    def view_blockchain(self):
        """
        Returns the blockchain
        """
        for block in self.blockchain.chain:
            print("Block index: ", block.index)
            print("Block validator: ", block.validator)
            print("Block previous hash: ", block.previous_hash)
            print("Block hash: ", block.current_hash)
            print("Block transactions: ")
            for transaction in block.transactions:
                print(transaction.payload())
            print("\n")
        