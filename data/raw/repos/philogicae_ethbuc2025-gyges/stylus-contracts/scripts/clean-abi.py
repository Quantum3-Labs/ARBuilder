#!/home/philogicae/.pyenv/shims/python
from json import dumps, loads
from os import path

current_dir = path.dirname(path.abspath(__file__))
with open(path.join(current_dir, "abi.json"), "r", encoding="utf-8") as f:
    contract_abi = loads(f.read().split("ABI")[1])

with open(path.join(current_dir, "abi.json"), "w", encoding="utf-8") as f:
    f.write(dumps(contract_abi))
