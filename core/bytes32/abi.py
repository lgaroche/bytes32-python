abi = [
    {"inputs": [], "name": "WrongSignature", "type": "error"},
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "key",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "bytes32",
                "name": "head",
                "type": "bytes32",
            },
        ],
        "name": "Publication",
        "type": "event",
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "heads",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "nonces",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "head", "type": "bytes32"}],
        "name": "publish",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "signer", "type": "address"},
            {"internalType": "bytes32", "name": "head", "type": "bytes32"},
            {"internalType": "bytes", "name": "signature", "type": "bytes"},
        ],
        "name": "publishFor",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]
