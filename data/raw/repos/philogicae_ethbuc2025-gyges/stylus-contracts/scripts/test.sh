. ./.env

#cargo stylus check -e $RPC_URL
cargo stylus deploy --private-key $PRIV_KEY -e $RPC_URL --contract-address $STYLUS_CONTRACT_ADDRESS --no-verify #--estimate-gas
cargo stylus export-abi --json --output ./scripts/abi.json && ./scripts/clean-abi.py
cast send --private-key $PRIV_KEY -r=$RPC_URL --value 10000000000000000000 $WALLET_2 2>&1 | echo "Wallet_2 funded"

#--------------------------

cast send --private-key $PRIV_KEY -r=$RPC_URL --json $STYLUS_CONTRACT_ADDRESS "registerUsername(string)" "player1" 2>&1 | tee ./scripts/output.txt | ./scripts/decode.py
cast send --private-key $PRIV_KEY_2 -r=$RPC_URL --json $STYLUS_CONTRACT_ADDRESS "registerUsername(string)" "player2" 2>&1 | tee ./scripts/output.txt | ./scripts/decode.py

#cast call --private-key $PRIV_KEY -r=$RPC_URL --json $STYLUS_CONTRACT_ADDRESS "getAddressByUsername(string)(address)" "salut" 2>&1 | tee ./scripts/output.txt | ./scripts/decode.py
#cast call --private-key $PRIV_KEY -r=$RPC_URL --json $STYLUS_CONTRACT_ADDRESS "getPlayerByAddress(address)((string, uint256, uint256, uint256[]))" $WALLET 2>&1 | tee ./scripts/output.txt | ./scripts/decode.py

cast send --private-key $PRIV_KEY -r=$RPC_URL --json $STYLUS_CONTRACT_ADDRESS "newGame(string)" "player2" 2>&1 | tee ./scripts/output.txt | ./scripts/decode.py
cast call --private-key $PRIV_KEY -r=$RPC_URL --json $STYLUS_CONTRACT_ADDRESS "getPlayerByUsername(string)((address, uint256, uint256, uint256[]))" "player1" 2>&1 | tee ./scripts/output.txt | ./scripts/decode.py
cast call --private-key $PRIV_KEY -r=$RPC_URL --json $STYLUS_CONTRACT_ADDRESS "getPlayerByUsername(string)((address, uint256, uint256, uint256[]))" "player2" 2>&1 | tee ./scripts/output.txt | ./scripts/decode.py
cast call --private-key $PRIV_KEY -r=$RPC_URL --json $STYLUS_CONTRACT_ADDRESS "gameById(uint256)((address, address, bytes32))" "0" 2>&1 | tee ./scripts/output.txt | ./scripts/display.py

# T1-P1
cast send --private-key $PRIV_KEY -r=$RPC_URL --json $STYLUS_CONTRACT_ADDRESS "play(uint256[])" "[5,3,0, 3,2,0]" 2>&1 | tee ./scripts/output.txt | ./scripts/decode.py
cast call --private-key $PRIV_KEY -r=$RPC_URL --json $STYLUS_CONTRACT_ADDRESS "gameById(uint256)((address, address, bytes32))" "0" 2>&1 | tee ./scripts/output.txt | ./scripts/display.py

# T1-P2
cast send --private-key $PRIV_KEY_2 -r=$RPC_URL --json $STYLUS_CONTRACT_ADDRESS "play(uint256[])" "[0,2,0, 3,2,1, 2,4,0]" 2>&1 | tee ./scripts/output.txt | ./scripts/decode.py
cast call --private-key $PRIV_KEY_2 -r=$RPC_URL --json $STYLUS_CONTRACT_ADDRESS "gameById(uint256)((address, address, bytes32))" "0" 2>&1 | tee ./scripts/output.txt | ./scripts/display.py

# T2-P1
cast send --private-key $PRIV_KEY -r=$RPC_URL --json $STYLUS_CONTRACT_ADDRESS "play(uint256[])" "[5,2,0, 4,2,0]" 2>&1 | tee ./scripts/output.txt | ./scripts/decode.py
cast call --private-key $PRIV_KEY -r=$RPC_URL --json $STYLUS_CONTRACT_ADDRESS "gameById(uint256)((address, address, bytes32))" "0" 2>&1 | tee ./scripts/output.txt | ./scripts/display.py

# T2-P2
cast send --private-key $PRIV_KEY_2 -r=$RPC_URL --json $STYLUS_CONTRACT_ADDRESS "play(uint256[])" "[0,4,0, 2,4,1, 3,2,1, 4,0,0]" 2>&1 | tee ./scripts/output.txt | ./scripts/decode.py
cast call --private-key $PRIV_KEY_2 -r=$RPC_URL --json $STYLUS_CONTRACT_ADDRESS "gameById(uint256)((address, address, bytes32))" "0" 2>&1 | tee ./scripts/output.txt | ./scripts/display.py

# T3-P1
cast send --private-key $PRIV_KEY -r=$RPC_URL --json $STYLUS_CONTRACT_ADDRESS "play(uint256[])" "[5,1,0, 4,2,2, 2,2,0]" 2>&1 | tee ./scripts/output.txt | ./scripts/decode.py
cast call --private-key $PRIV_KEY -r=$RPC_URL --json $STYLUS_CONTRACT_ADDRESS "gameById(uint256)((address, address, bytes32))" "0" 2>&1 | tee ./scripts/output.txt | ./scripts/display.py

#--------------------------

#stylus-interpreter -s $WALLET -b $(cast bn --rpc-url $RPC_URL) --addr $STYLUS_CONTRACT_ADDRESS -u $RPC_URL gyges.wasm $(cast calldata "newGame(string)(uint256)" "salut")