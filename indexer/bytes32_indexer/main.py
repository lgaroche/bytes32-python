import os
from datetime import datetime, timezone
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
def get_dag(path):
    url = f"{ipfs_api}/dag/get?arg={path}"
    r = requests.post(url, headers={"Accept": "application/json"})
    if r.status_code != 200:
        print(f"failed to read from ipfs (status={r.status_code}): {path}")
        raise Exception
    return r.json()


def resolve_dag(path):
    url = f"{ipfs_api}/dag/resolve?arg={path}"
    r = requests.post(url, headers={"Accept": "application/json"})
    if r.status_code != 200:
        print(f"failed to read from ipfs (status={r.status_code}): {path}")
        raise Exception
    return CID.decode(r.json()["Cid"]["/"])


def read_updates(path):
    visited = []

    def read_inner(path):
        cid = resolve_dag(path)

        # do not loop into repeated paths
        if cid in visited:
            return []

        dag = get_dag(cid)
        docs = []
        if "updates" in dag:
            try:
                docs += read_inner(f"{path}/updates")
            except Exception as e:
                print(f"failed to read updates in {path}")
                print(e)
        elif "items" in dag:
            for item in dag["items"]:
                try:
                    docs += read_inner(f"{path}/items/{item}")
                except Exception as e:
                    print(f"failed to read updates in {path}/items/{item}")
                    continue
        elif "content" in dag:
            try:
                entry = SignedEntry(**dag)
                doc = {
                    "id": str(cid),
                    "signer": entry.signer(),
                    "signature.format": entry.signature.format,
                    "signature.schema": entry.signature.signature_schema.link,
                    "signature.sig": entry.signature.sig,
                    "content.type": entry.content.type,
                    "content.text": entry.content.text,
                    "content.data": entry.content.data.link,
                    "ref": entry.ref.link,
                }
                docs += [doc]
            except Exception as e:
                print(e)
        return docs

    return read_inner(path)


def handle_logs(logs):
    print(f"start handling {len(logs)} logs")
    for log in logs:
        key = log.args.key
        head = log.args.head

        cid = CID(base="base32", version=1, codec="dag-cbor", digest=("sha2-256", head))
        print(f"new head for: {key} => {cid}")

        try:
            docs = read_updates(cid)
            block = w3.eth.get_block(log.blockNumber)
            block_time = datetime.fromtimestamp(
                block.timestamp, tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
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
