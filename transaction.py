"""Transaction class to represent a transaction in the blockchain."""

import time
from wallet import Wallet
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
        type_of_transaction="coins",
    ):
        self.sender_address = sender_address
        self.receiver_address = receiver_address
        self.amount = amount
        self.message = message
        self.type_of_transaction = type_of_transaction  # Can be 'coins' or 'message'
        self.nonce = nonce
        self.timestamp = time.time()
        self.transaction_id = self.calculate_transaction_id()
        self.signature = ""

    def calculate_transaction_id(self):
        """
        Calculate the transaction ID.
        """
        transaction_dict = {
            "sender_address": self.sender_address,
            "receiver_address": self.receiver_address,
            "amount": self.amount,
            "message": self.message,
            "type_of_transaction": self.type_of_transaction,
            "nonce": self.nonce,
            "timestamp": self.timestamp,
        }
        return BlockChainUtils.hash(transaction_dict).hexdigest()

    def equals(self, transaction):
        """
        Check if two transactions are equal.
        """
        if self.transaction_id == transaction.transaction_id:
            return True
        else:
            return False

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
            "timestamp": self.timestamp,
            "transaction_id": self.transaction_id,
            "signature": self.signature,
        }

    def payload(self):
        """
        Generate the payload for the transaction.
        """
        return {
            "sender_address": self.sender_address,
            "receiver_address": self.receiver_address,
            "amount": self.amount,
            "message": self.message,
            "type_of_transaction": self.type_of_transaction,
            "nonce": self.nonce,
            "timestamp": self.timestamp,
            "transaction_id": self.transaction_id,
        }

    def sign_transaction(self, wallet):
        """
        Sign the transaction with a wallet's private key.
        """
        self.signature = wallet.sign_transaction(self.payload())

    @staticmethod
    def verify_transaction_signature(transaction, signature, sender_public_key):
        """
        Verify the transaction's signature.
        """
        return Wallet.verify_transaction(
            transaction.payload(), signature, sender_public_key
        )

    def is_valid(self):
        """
        Validates the transaction data.
        """
        # Check for a valid signature
        if not self.signature or not Transaction.verify_transaction_signature(
            self, self.signature, self.sender_address
        ):
            return False
        # Additional validation checks can be implemented here
        return True
