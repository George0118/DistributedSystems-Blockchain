"""For creating and managing key pairs"""

from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from blockchain_utils import BlockChainUtils
from transaction import Transaction


class Wallet:
    """
    For creating and managing key pairs
    """

    def __init__(self):
        """
        Generate a pair of RSA keys.
        """
        self.key_pair = RSA.generate(2048)
        self.private_key = self.key_pair.export_key()
        self.public_key = self.key_pair.publickey().export_key()
        self.nonce = 0

    # @staticmethod
    # def generate_keys():

    #     key = RSA.generate(2048)
    #     private_key = key.export_key()
    #     public_key = key.publickey().export_key()
    #     return private_key, public_key

    def from_key(self, file):
        """
        Load a key pair from a file.
        """
        key = ""
        with open(file, "r", encoding="utf-8") as f:
            key = RSA.importKey(f.read())
        self.key_pair = key
        self.private_key = key.export_key()
        self.public_key = key.publickey().export_key()
        self.nonce = 0

    def sign_transaction(self, transaction: Transaction):
        """
        Sign a transaction with the private key.
        """
        signer = pkcs1_15.new(RSA.import_key(self.private_key))  # Create a signer

        hash_of_transaction = BlockChainUtils.hash(transaction.payload())

        signature = signer.sign(hash_of_transaction)
        return signature.hex()

    @staticmethod
    def verify_signature(transaction):
        """
        Verify the signature of a transaction.
        """
        sender_public_key = transaction.sender_address
        public_key = RSA.import_key(sender_public_key)
        verifier = pkcs1_15.new(public_key)  # Create a verifier

        signature = bytes.fromhex(transaction.signature)

        hash_of_transaction = BlockChainUtils.hash(transaction.payload())
        try:
            verifier.verify(hash_of_transaction, signature)
            return True
        except (ValueError, TypeError):
            return False

    # def create_block(self, transactions, previous_hash, index):
    #     """
    #     Create a block.
    #     """
    #     block = Block(
    #         transactions=transactions,
    #         previous_hash=previous_hash,
    #         validator=self.public_key.decode("utf-8"),
    #         index=index,
    #     )
    #     return block

    def create_transaction(
        self, receiver_address, amount, message, type_of_transaction
    ):
        """
        Create a transaction.
        """
        transaction = Transaction(
            sender_address=self.public_key.decode("utf-8"),
            receiver_address=receiver_address,
            amount=amount,
            nonce=self.nonce,
            message=message,
            type_of_transaction=type_of_transaction,
        )
        self.nonce += 1
        signature = self.sign_transaction(transaction)
        transaction.signature = signature
        return transaction
