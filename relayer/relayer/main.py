import os
import threading
import time
import queue
import json
from typing import Mapping
from fastapi import FastAPI, HTTPException

import requests
import uvicorn
import dag_cbor
from multiformats import CID
import hashlib
from hexbytes import HexBytes

from bytes32 import w3
from bytes32.model import Head, PartialHead


from web3.exceptions import TransactionNotFound
from eth_account.messages import encode_defunct

contract_address = os.getenv("BYTES32_CONTRACT")
private_key = os.getenv("PRIVATE_KEY")
ipfs_api = os.getenv("IPFS_API_URL")


app = FastAPI()
heads: Mapping[str, CID] = {}
q = queue.Queue()

latest = w3.eth.get_block("latest")
account = w3.eth.account.from_key(private_key)
print(f"latest block number: {latest.number}")
print(f"using {account.address}")

with open("../contract/out/Bytes32.sol/Bytes32.json", "r") as f:
    abi = json.load(f)["abi"]
    bytes32 = w3.eth.contract(address=contract_address, abi=abi)


def aggregate():
    print("start aggregate thread")
    while True:
        empty = q.empty()
        while not q.empty():
            (pkh, cid) = q.get()
            heads[pkh] = CID.decode(cid)

        if not empty:
            aggr_cid = ipfs_add_and_pin(
                {
                    "@context": "https://bytes32.org/contexts/aggregate.jsonId",
                    "heads": heads,
                }
            )
            print(f"new aggregate cid: {aggr_cid}")

            digest = CID.decode(aggr_cid).raw_digest.hex()
            print(digest)

            nonce = w3.eth.get_transaction_count(account.address)

            tx = bytes32.functions.publish(head=HexBytes(digest)).build_transaction(
                {
                    "maxFeePerGas": w3.toWei("2", "gwei"),
                    "maxPriorityFeePerGas": w3.toWei("1", "gwei"),
                    "gas": 75000,
                    "nonce": nonce,
                }
            )
            signed_tx = account.sign_transaction(tx)
            est = w3.eth.estimate_gas(tx)
            print(est)
            res = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            print(f"sent transaction: {w3.toHex(res)}")

            receipt = None
            while receipt is None:
                try:
                    receipt = w3.eth.get_transaction_receipt(res)
                    print(f"transaction was included in block {receipt.blockNumber}")
                except TransactionNotFound:
                    time.sleep(5)

        time.sleep(2)


threading.Thread(target=aggregate, daemon=True).start()


def ipfs_add_and_pin(obj):
    url = f"{ipfs_api}/dag/put?input-codec=dag-cbor&pin=true"
    dag = dag_cbor.encode(obj)
    r = requests.post(url, files={"file": dag}, headers={"Accept": "application/json"})
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail="failed to publish on ipfs")
    return r.json()["Cid"]["/"]


@app.post("/publish")
async def publish(head: Head):

    # check signature
    recover = head.id.pkh
    if head.sig != "fake":
        partial = PartialHead.parse_obj(head)
        print(partial.dict(by_alias=True))
        cbor = dag_cbor.encode(partial.dict(by_alias=True))
        digest = hashlib.sha256(cbor).digest()
        message = encode_defunct(digest)
        recover = w3.eth.account.recover_message(message, signature=head.sig)

    # if recover is not head.id.pkh:
    #    raise HTTPException(status_code=403, detail="Wrong signature")

    # publish on ipfs
    cid = ipfs_add_and_pin(head.dict(by_alias=True))

    # update head on contract
    q.put((head.id.pkh, cid))

    return {"recover": recover, "cid": cid}


def main():
    uvicorn.run("relayer.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
