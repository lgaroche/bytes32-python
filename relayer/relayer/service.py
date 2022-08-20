import os
import threading
import time
import queue
from typing import Mapping

from fastapi import FastAPI
from pydantic import BaseModel
from multiformats import CID
from hexbytes import HexBytes
from web3.auto import w3
from http.client import HTTPException

from bytes32 import SignedEntry
from bytes32.utils import bytes32_contract, ipfs_add_and_pin, last_head_cid


contract_address = os.getenv("BYTES32_CONTRACT")
private_key = os.getenv("PRIVATE_KEY")
ipfs_api = os.getenv("IPFS_API_URL")


def pin_aggregate(items):
    aggregate_ctx = {"@context": "https://bytes32.org/contexts/aggregate.jsonId"}
    return CID.decode(ipfs_add_and_pin({**aggregate_ctx, "items": items}))


app = FastAPI()
last_tx_hashes: Mapping[str, bytes] = {}
q = queue.Queue()

latest = w3.eth.get_block("latest")
account = w3.eth.account.from_key(private_key)
print(f"latest block number: {latest.number}")
print(f"using {account.address}")


try:
    last_head = last_head_cid(w3, account.address)
    print(last_head)
except ValueError:
    print("failed to decode last aggregate")
    last_head = ""


def aggregate():
    print("start aggregate thread")
    while True:
        empty = q.empty()
        updates: Mapping[str, CID] = {}
        while not q.empty():
            (pkh, cid) = q.get()
            updates[pkh] = CID.decode(cid)

        if not empty:
            last_head = ipfs_add_and_pin(
                {
                    "updates": pin_aggregate(updates),
                    "last_tx_hashes": pin_aggregate(last_tx_hashes),
                }
            )
            print(f"new aggregate cid: {last_head}")
            digest = CID.decode(last_head).raw_digest.hex()
            receipt = bytes32_contract(w3).publish(head=HexBytes(digest)).send(account)
            last_tx_hashes[pkh] = receipt.transactionHash

        time.sleep(5)


threading.Thread(target=aggregate, daemon=True).start()


@app.get("/signer")
async def signer():
    return {"signer": account.address}


@app.post("/publish")
async def publish(entry: SignedEntry):

    signer = entry.signer()
    # TODO: check ref to deny replays

    # publish on ipfs
    cid = entry.publish()

    # update entry on contract
    q.put((signer, cid))

    return {
        "current_aggregate": str(last_head),
        "cid": cid,
        "signer": account.address,
    }


class DelegateRequest(BaseModel):
    signer: str
    delegate: str
    signature: str


@app.post("/delegate")
async def delegate(request: DelegateRequest):
    if request.delegate != account.address:
        raise HTTPException(403, f"this relayer can only delegate to {account.address}")

    try:
        return (
            bytes32_contract(w3)
            .publishFor(request.signer, request.delegate, request.signature)
            .send(account)
        )
    except:
        print("delegate tx failed")
