# EthBucharest 2025 - Gyges

Implementation of [Gyges](https://boardspace.net/english/about_gyges.html), a strategy board game.

Why this game? Because nobody knows it and the rules seem to be simple on paper... but the game is actually complex and pretty deep when we take a closer look (like Go).

The duration of a game can go from 10 seconds to 2 hours, if the levels of the players are close.

As a solidity dev, it was the perfect opportunity to discover Arbitrum Stylus, refresh my Rust, and have fun with low-level optimizations (Yes it's FUN).

## How to play

Read the rules: [here](https://boardspace.net/english/about_gyges.html)

## Stack

- Rust language
- [Arbitrum Stylus](https://arbitrum.io/stylus)
- [Nitro-devnode](https://docs.arbitrum.io/run-arbitrum-node/run-nitro-dev-node) for local tests
- Some python/bash scripts as minimal CLI

## Notes

Tbh I focused on understanding the specificities of Rust/Stylus and optimizing EVM storage (The state of the game fits on a single bytes32).

Didn't have time to:
- Restrict paths properly: should not be able to pass by an occupied cell or a cell already used during the turn.
- Placement restriction when 'flying' (after replacing a piece): can place a piece on any empty cell, but should not be able to go behind the opponent line.

## TODO's

* Improve the smart contract:
    - Heavy refactoring
    - Add missing restrictions
    - Add winner check
* Build the webUI (probably with React)
* Add AI opponent using LLM agent