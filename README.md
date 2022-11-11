# Bytes32

> :warning: **This is an experimental proof-of-concept**: Use at your own risks

Python implementation of the bytes32 protocol.

## Introduction

Bytes32 is an attempt at designing a decentralized yet user friendly social publishing platform.

### Censorship resistance

Bytes32 is an open protocol. Anyone can compose and sign arbitrary messages that can be published on the blockchain.
Content moderation is done at the reader's level and discretion. Relayers and indexers are more centralized infrastructure that are free to perform any content curation or moderation that they see fit. Users will be able to chose whether to host their own indexer and relayer, or connect to a publicly available one.

## How does it work

### Overview

Messages (that can be anything from social updates, news articles, to git commits...) are posted to the IPFS network as an IPLD document (dag-cbor encoded) and its hash is published on a smart contract. Each message is linked to the previous one with either its last hash or the last blockchain transaction.
To simplify onboarding, relayers can publish content on behalf of the users to subsidize the transaction fees.

### Detailed

> TODO

### Python libraries and tools

This mono-repository is an implementation of the core protocol, an indexer and a relayer

## Installation and usage

> TODO
