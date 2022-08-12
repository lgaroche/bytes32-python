from web3.auto import w3
from web3.types import TxReceipt
from eth_account.account import Account

from bytes32 import Entry

private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
account = Account.from_key(private_key)


def test_publish():

    print(w3.clientVersion)

    # create and sign entry
    content = {"type": "text/plain", "data": "this is a test"}
    entry = Entry(content=content)
    signed = entry.sign(account)
    assert signed.signer() == account.address

    # publish on ipfs
    cid = signed.publish()
    assert cid is not None

    # commit on the chain
    receipt: TxReceipt = signed.commit(w3, account)
    assert receipt.status == 1
