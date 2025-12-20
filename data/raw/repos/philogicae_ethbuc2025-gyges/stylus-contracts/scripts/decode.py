#!/home/philogicae/.pyenv/shims/python
from json import load, loads
from os import path

from eth_abi import decode as eth_abi_decode
from rich import print as rprint
from web3 import Web3

current_dir = path.dirname(path.abspath(__file__))
with open(path.join(current_dir, "output.txt"), "r", encoding="utf-8") as f:
    data = f.read().strip()

if data.startswith("Error:"):
    if "-32000" in data:
        rprint("Error: execution reverted")
        exit()
    data = data.split("data: ")[1][1:-1]
elif data.startswith("["):
    rprint(loads(data))
    exit()
else:
    exit()

with open(path.join(current_dir, "abi.json"), "r", encoding="utf-8") as f:
    contract_abi = load(f)

w3 = Web3()
selector = data[2:10]

# Errors
if isinstance(data, str):
    for item in contract_abi:
        if item["type"] == "error":
            signature = (
                f"{item['name']}({','.join([inp['type'] for inp in item['inputs']])})"
            )
            calculated_selector = w3.keccak(text=signature).hex()[:8]
            if calculated_selector == selector:
                input_types = [inp["type"] for inp in item["inputs"]]
                decoded_args = eth_abi_decode(input_types, bytes.fromhex(data[10:]))
                rprint(f"-> {item['name']}{decoded_args}")
                exit()
    rprint("No matching error found.")
