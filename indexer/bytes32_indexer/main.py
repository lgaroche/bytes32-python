import os
from datetime import datetime
from functools import lru_cache

import pysolr
import requests
from multiformats import CID
from web3.auto import w3

from bytes32_indexer import logs

from bytes32.utils import bytes32_events
from bytes32 import SignedEntry

contract_address = os.getenv("BYTES32_CONTRACT")
ipfs_api = os.getenv("IPFS_API_URL")
solr_url = os.getenv("SOLR_URL")


solr = pysolr.Solr(solr_url, always_commit=True)
solr.ping()

latest = w3.eth.get_block("latest")
print(f"latest block number: {latest.number}")


@lru_cache(maxsize=4096)
def get_dag(cid):
    url = f"{ipfs_api}/dag/get?arg={cid}"
    r = requests.post(url, headers={"Accept": "application/json"})
    if r.status_code != 200:
        print(f"failed to read from ipfs (status={r.status_code}): {cid}")
        raise Exception
    return r.json()


def traverse(path):
    head_obj = get_dag(path)
    docs = []
    if "heads" in head_obj:
        for h in head_obj["heads"]:
            try:
                docs += traverse(head_obj["heads"][h]["/"])
            except Exception as e:
                print(f"failed to traverse: {e}")
                continue
    elif "content" in head_obj:
        entry = SignedEntry(**head_obj)
        doc = {
            "id": path,
            "signer": entry.signer(),
            "sig": entry.sig,
            "content.type": entry.content.type,
            "content.data": entry.content.data,
        }
        if "ref" in head_obj and "/" in head_obj["ref"]:
            doc["ref"] = head_obj["ref"]["/"]
        docs += [doc]
    return docs


def handle_logs(logs):
    print(f"start handling {len(logs)} logs")
    for log in logs:
        key = log.args.key
        head = log.args.head

        cid = CID(base="base32", version=1, codec="dag-cbor", digest=("sha2-256", head))
        print(f"new head for: {key} => {cid}")

        try:
            docs = traverse(cid)
            block = w3.eth.get_block(log.blockNumber)
            block_time = datetime.fromtimestamp(block.timestamp).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            for doc in docs:
                doc["block.time"] = block_time
                doc["block.number"] = log.blockNumber
                # print(doc)
            solr.add(docs)
            print(get_dag.cache_info())
        except Exception as e:
            print(e)
            continue


logs.fetch_logs(
    w3=w3,
    start_block=0,
    event=bytes32_events(w3).Publication(),
    handle_logs=handle_logs,
)
