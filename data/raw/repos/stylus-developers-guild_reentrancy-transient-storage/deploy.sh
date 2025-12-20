#!/bin/sh -eu

wasm_file=$1

cargo stylus deploy \
	--endpoint $SPN_SUPERPOSITION_URL \
	--wasm-file "$wasm_file" \
	--no-verify \
	--private-key $SPN_SUPERPOSITION_KEY \
	        | sed -nr 's/.*deployed code at address: +.*(0x.{40}).*$/\1/p'
