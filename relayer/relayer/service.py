import os
import threading
import time
import queue
from typing import Mapping

from fastapi import FastAPI
from multiformats import CID
from hexbytes import HexBytes
from eth_account.messages import encode_defunct
from web3.auto import w3

from bytes32 import SignedEntry
from bytes32.utils import bytes32_contract, ipfs_add_and_pin


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


def aggregate():
    print("start aggregate thread")
    while True:
        empty = q.empty()
        updates: Mapping[str, CID] = {}
        while not q.empty():
            (pkh, cid) = q.get()
            updates[pkh] = CID.decode(cid)

        if not empty:
            aggr_cid = ipfs_add_and_pin(
                {
                    "updates": pin_aggregate(updates),
                    "last_tx_hashes": pin_aggregate(last_tx_hashes),
                }
            )
            print(f"new aggregate cid: {aggr_cid}")
            digest = CID.decode(aggr_cid).raw_digest.hex()
            receipt = bytes32_contract(w3).publish(account, head=HexBytes(digest))
            last_tx_hashes[pkh] = receipt.transactionHash

        time.sleep(2)


threading.Thread(target=aggregate, daemon=True).start()


@app.post("/publish")
async def publish(entry: SignedEntry):

    signer = entry.signer()
    # TODO: check ref to deny replays

    # publish on ipfs
    cid = entry.publish()

    # update entry on contract
    q.put((signer, cid))

    return {"cid": cid}
