import os
import time

import dag_cbor
import requests
from web3 import Web3
from eth_account import Account
from web3.exceptions import TransactionNotFound

from bytes32.abi import abi


ipfs_api = os.getenv("IPFS_API_URL")
contract_address = os.getenv("BYTES32_CONTRACT")


def ipfs_add_and_pin(obj):
    url = f"{ipfs_api}/dag/put?input-codec=dag-cbor&pin=true"
    stripped = {k: v for k, v in obj.items() if v is not None}
    dag = dag_cbor.encode(stripped)
    r = requests.post(url, files={"file": dag}, headers={"Accept": "application/json"})
    if r.status_code != 200:
        raise Exception("failed to publish on ipfs")
    return r.json()["Cid"]["/"]


def bytes32_contract(w3: Web3):
    """Access contract functions, sign and send them directly with a local private key"""
    bytes32 = w3.eth.contract(address=contract_address, abi=abi)
    f = vars(bytes32.functions)

    def sign_and_send(account: Account, fun, *args, **kwargs):
        nonce = w3.eth.get_transaction_count(account.address)
        tx = bytes32.functions[fun](*args, **kwargs).build_transaction(
            {
                "maxFeePerGas": w3.toWei("2", "gwei"),
                "maxPriorityFeePerGas": w3.toWei("1", "gwei"),
                "gas": 75000,
                "nonce": nonce,
            }
        )
        signed_tx = account.sign_transaction(tx)
        res = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"sent transaction: {w3.toHex(res)}")

        receipt = None
        while receipt is None:
            try:
                receipt = w3.eth.get_transaction_receipt(res)
                print(f"transaction was included in block {receipt.blockNumber}")
                return receipt
            except TransactionNotFound:
                time.sleep(5)

    def call(fun):
        return lambda account, *args, **kwargs: sign_and_send(
            account, fun, *args, **kwargs
        )

    class dotdict(dict):
        """
        dot.notation access to dictionary attributes
        thanks derek73: https://stackoverflow.com/a/23689767
        """

        __getattr__ = dict.get
        __setattr__ = dict.__setitem__
        __delattr__ = dict.__delitem__

    return dotdict({k: call(k) for k, v in f.items() if callable(v)})
