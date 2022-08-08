# from web3.auto import w3
import os
from web3 import Web3

eth_rpc = os.getenv("ETH_RPC_URL")

w3 = Web3(Web3.HTTPProvider(eth_rpc))
from web3.middleware import geth_poa_middleware

w3.middleware_onion.inject(geth_poa_middleware, layer=0)
print(w3.clientVersion)
