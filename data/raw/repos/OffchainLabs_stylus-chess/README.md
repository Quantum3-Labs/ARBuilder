![Image](./header.png)

# Stylus Chess

Demonstrates the usage of an off-the-shelf chess engine from the Rust crates.io package registry to quickly build an onchain chess contract.

## Requirements For Deployment

- [Rust lang](https://www.rust-lang.org/tools/install)
- [nitro testnode](https://docs.arbitrum.io/stylus/how-tos/local-stylus-dev-node) (requires docker)
- [cargo stylus](https://docs.arbitrum.io/stylus/stylus-quickstart#creating-a-stylus-project)
- [cast](https://book.getfoundry.sh/getting-started/installation) (part of the Foundry CLI suite)

## ABI

### `totalGames()(uint256)`

Returns total number of games that have been created on this contract.

`cast call --rpc-url 'http://localhost:8547' --private-key PRIVATE_KEY_HERE DEPLOYMENT_ADDRESS_HERE "totalGames()(uint256)" GAME_NUMBER_HERE`

### `getTurnColor(uint256 game_number)(uint256)`

Gets the turn color for a given game number. Can either be 0 for WHITE or 1 for BLACK.

`cast call --rpc-url 'http://localhost:8547' --private-key PRIVATE_KEY_HERE DEPLOYMENT_ADDRESS_HERE "getTurnColor(uint256)(uint256)" GAME_NUMBER_HERE`

### `getCurrentPlayer(uint256 game_number)(address)`

Returns the address of the current player who has next move for a given game number.

`cast call --rpc-url 'http://localhost:8547' --private-key PRIVATE_KEY_HERE DEPLOYMENT_ADDRESS_HERE "getCurrentPlayer(uint256)(address)" GAME_NUMBER_HERE`

### `playMove(uint256 game_number, uint256 from_row, uint256 from_col, uint256 to_row, uint256 to_col)(uint256)`

Attempts to play a move for a given game number. Must pass in the current row and column for the piece and the desired row and column. Will return a status code for the attempted move, which will either be 1 for CONTINUING, 2 for ILLEGAL_MOVE, 3 for STALE_MATE or 4 for VICTORY.

NOTE: This mutates state, so it must be written to the chain with a send.

`cast send --rpc-url 'http://localhost:8547' --private-key PRIVATE_KEY_HERE DEPLOYMENT_ADDRESS_HERE "playMove(uint256, uint256, uint256, uint256, uint256)(uint256)" GAME_NUMBER_HERE FROM_ROW_HERE FROM_COL_HERE TO_ROW_HERE TO_COL_HERE`

### `printGameState(uint256 game_number)`

NOTE: This will only work locally and should be removed for any public testnet or mainnet.

This will print the state of the chess board to the Stylus console window when running an Arbitrum Nitro testnode locally. It uses unicode symbols to present an 8x8 grid in the console window.

`cast call --rpc-url 'http://localhost:8547' --private-key PRIVATE_KEY_HERE DEPLOYMENT_ADDRESS_HERE "printGameState(uint256)()" GAME_NUMBER_HERE`

### `boardStateByGameNumber(uint256 game_number)(uint256)`

Returns the uint256 that represents the board state for a given game number.

`cast call --rpc-url 'http://localhost:8547' --private-key PRIVATE_KEY_HERE DEPLOYMENT_ADDRESS_HERE "boardStateByGameNumber(uint256)(uint256)" GAME_NUMBER_HERE`

### `createOrJoin()(uint256)`

NOTE: This mutates state so it must be sent as an actual transaction.

This will either create a pending game to await a second player or will join the currently existing pending game.

`cast send --rpc-url 'http://localhost:8547' --private-key PRIVATE_KEY_HERE DEPLOYMENT_ADDRESS_HERE "createOrJoin()(uint256)"`

## Other Stylus Resources

- [Stylus Rust SDK](https://docs.arbitrum.io/stylus/reference/rust-sdk-guide)
- [Stylus By Example](https://arbitrum-stylus-by-example.vercel.app/basic_examples/hello_world)
- [Awesome Stylus](https://github.com/OffchainLabs/awesome-stylus)
- [Arbitrum Stylus Devs Telegram](https://t.me/arbitrum_stylus)
