"""Transaction class to represent a transaction in the blockchain."""

from blockchain_utils import BlockChainUtils


class Transaction:
    """
    Transaction class to represent a transaction in the blockchain.
    """

    def __init__(
        self,
        sender_address,
        receiver_address,
        amount,
        nonce,
        message="",
        type_of_transaction="DEFAULT",
    ):
        self.sender_address = sender_address
        self.receiver_address = receiver_address
        self.amount = amount
        self.message = message
        self.type_of_transaction = (
            type_of_transaction  # Can be 'DEFAULT' or 'STAKE' or 'EXCHANGE
        )
        self.nonce = nonce
        self.transaction_id = self.calculate_transaction_id()
        self.signature = None
        self.fee = (
            0.03 * amount + len(message) if type_of_transaction == "DEFAULT" else 0
        )

    def calculate_transaction_id(self):
        """
        Calculate the transaction ID (to_dict without signature and id).
        """
        transaction_dict = {
            "sender_address": self.sender_address,
            "receiver_address": self.receiver_address,
            "amount": self.amount,
            "message": self.message,
            "type_of_transaction": self.type_of_transaction,
            "nonce": self.nonce,
        }
        return BlockChainUtils.hash(transaction_dict).hexdigest()

    def payload(self):
        """
        Generate the payload for the transaction (to_dict without signature).
        """
        return {
            "sender_address": self.sender_address,
            "receiver_address": self.receiver_address,
            "amount": self.amount,
            "message": self.message,
            "type_of_transaction": self.type_of_transaction,
            "nonce": self.nonce,
            "transaction_id": self.transaction_id,
        }

    def to_dict(self):
        """
        Convert the transaction to a dictionary, without signature.
        """
        return {
            "sender_address": self.sender_address,
            "receiver_address": self.receiver_address,
            "amount": self.amount,
            "message": self.message,
            "type_of_transaction": self.type_of_transaction,
            "nonce": self.nonce,
            "transaction_id": self.transaction_id,
            "signature": self.signature,
        }

    def equals(self, transaction):
        """
        Check if two transactions are equal.
        """
        return self.transaction_id == transaction.transaction_id

    def sign_transaction(self, signature):
        """
        Sign the transaction with a wallet's private key.
        """
        self.signature = signature
