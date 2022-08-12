import os
import hashlib
import dag_cbor

from typing import Union
from pydantic import BaseModel, Field
from multiformats import CID
from web3 import Web3
from eth_account.messages import encode_defunct
from eth_account.account import Account
from hexbytes import HexBytes

from bytes32.utils import bytes32_contract, ipfs_add_and_pin

__version__ = "0.0.1"

contract_address = os.getenv("BYTES32_CONTRACT")


class Content(BaseModel):
    type: str
    data: str


class IPLDLink(BaseModel):
    link: str = Field(..., title="/", alias="/")


class Entry(BaseModel):
    sub: Union[str, None] = None
    content: Union[Content, None] = None
    ref: Union[IPLDLink, None] = None

    def encode_and_hash(self):
        cbor = dag_cbor.encode(self.dict(by_alias=True))
        digest = hashlib.sha256(cbor).digest()
        return encode_defunct(digest)

    def sign(self, account: Account):
        message = self.encode_and_hash()
        return SignedEntry(
            **self.dict(by_alias=True),
            signer=account.address,
            sig=account.sign_message(message).signature.hex(),
        )


class SignedEntry(Entry):
    sig: str
    cid: Union[str, None] = None

    def signer(self):
        partial = Entry.parse_obj(self)
        message = partial.encode_and_hash()
        if self.sig == "fake":
            return "0xnull"
        return Account.recover_message(message, signature=self.sig)

    def publish(self):
        print(self.dict(by_alias=True))
        self.cid = ipfs_add_and_pin(self.dict(by_alias=True))
        return self.cid

    def commit(self, w3: Web3, account: Account):
        signer = self.signer()
        if account.address != signer:
            raise Exception(
                f"Wrong account ({account.address}): entry was signed by {signer}"
            )
        digest = CID.decode(self.cid).raw_digest.hex()
        return bytes32_contract(w3).publish(account, head=HexBytes(digest))
