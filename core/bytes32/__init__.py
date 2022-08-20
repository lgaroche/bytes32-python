import os

from typing import Union
from pydantic import BaseModel, Field
from multiformats import CID
from web3 import Web3
from eth_account.messages import SignableMessage
from eth_account._utils.structured_data.hashing import (
    hash_domain,
    hash_message as hash_eip712_message,
)
from eth_account.account import Account
from hexbytes import HexBytes

from bytes32.utils import bytes32_contract, ipfs_add_and_pin

__version__ = "0.0.1"

contract_address = os.getenv("BYTES32_CONTRACT")

eip721_bytes32_v1 = {
    "types": {
        "EIP712Domain": [
            {"name": "name", "type": "string"},
            {"name": "version", "type": "string"},
        ],
        "Link": [{"name": "/", "type": "string"}],
        "Content": [
            {"name": "type", "type": "string"},
            {"name": "text", "type": "string"},
            {"name": "data", "type": "Link"},
        ],
        "Entry": [
            {"name": "content", "type": "Content"},
            {"name": "meta", "type": "Link"},
            {"name": "ref", "type": "Link"},
        ],
    },
    "primaryType": "Entry",
    "domain": {"name": "Bytes32", "version": "1"},
}


class IPLDLink(BaseModel):
    link: str = Field(..., alias="/")


class Content(BaseModel):
    type: str
    text: str
    data: IPLDLink


class Entry(BaseModel):
    content: Content
    meta: IPLDLink
    ref: IPLDLink

    def encode_eip712(self):
        data = eip721_bytes32_v1.copy()
        data["message"] = self.dict(by_alias="/")
        # return encode_structured_data(data)
        return SignableMessage(
            HexBytes(b"\x01"),
            hash_domain(data),
            hash_eip712_message(data),
        )

    def sign(self, account: Account):
        message = self.encode_eip712()
        return SignedEntry(
            **self.dict(by_alias=True),
            signer=account.address,
            signature=Bytes32Signature(
                format="eip721-bytes32-v1",
                schema={
                    "/": "bafyreidsag4nrh3jf6qt634gnxu25eryxoonbamlggjes7a7pmkghu2gqa"
                },
                sig=account.sign_message(message).signature.hex(),
            ),
        )


class Bytes32Signature(BaseModel):
    format: str
    signature_schema: IPLDLink = Field(..., alias="schema")
    sig: str


class SignedEntry(Entry):
    signature: Bytes32Signature
    cid: Union[str, None] = None

    def signer(self):
        if self.signature.format == "fake":
            return "0xnull"
        partial = Entry.parse_obj(self)
        message = partial.encode_eip712()
        # TODO: reject malleable signatures:
        # https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/utils/cryptography/ECDSA.sol#L140
        return Account.recover_message(message, signature=self.signature.sig)

    def publish(self):
        self.cid = ipfs_add_and_pin(self.dict(by_alias=True))
        return self.cid

    def commit(self, w3: Web3, account: Account):
        signer = self.signer()
        if account.address != signer:
            raise Exception(
                f"Wrong account ({account.address}): entry was signed by {signer}"
            )
        digest = CID.decode(self.cid).raw_digest.hex()
        return bytes32_contract(w3).publish(head=HexBytes(digest)).send(account)
