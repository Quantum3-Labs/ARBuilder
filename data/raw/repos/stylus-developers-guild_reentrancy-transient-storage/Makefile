
WASM := target/wasm32-unknown-unknown/release/stylus_reentrant.wasm

.PHONY: build contract-1 contract-2

build: contract-1 contract-2

contract-1: contract-1.wasm
contract-2: contract-2.wasm

contract-1.wasm: $(shell find src -name '*.rs')
	@rm -f ${WASM}
	@cargo build --release --features contract-1
	@cp ${WASM} contract-1.wasm

contract-2.wasm: $(shell find src -name '*.rs')
	@rm -f ${WASM}
	@cargo build --release --features contract-2
	@cp ${WASM} contract-2.wasm
