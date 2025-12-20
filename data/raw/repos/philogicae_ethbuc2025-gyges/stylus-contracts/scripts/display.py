#!/home/philogicae/.pyenv/shims/python
from datetime import datetime
from json import load
from os import path

from rich import print as rprint

current_dir = path.dirname(path.abspath(__file__))
try:
    with open(path.join(current_dir, "output.txt"), "r", encoding="utf-8") as f:
        data = load(f)
except Exception as e:
    rprint(f"Error: {e}\nData: {f.read()}")
    exit()

player1, player2, state = data[0][1:-1].split(", ")
if player1 == "0x0000000000000000000000000000000000000000":
    rprint("Error: Game not found.")
    exit()

state = state[2:]
board, win_top, win_bottom, start, end, turn, player_turn = (
    state[0:36],
    state[36:38],
    state[38:40],
    state[40:48],
    state[48:56],
    state[56:62],
    state[62:64],
)


def timestamp_to_date(timestamp):
    return datetime.fromtimestamp(int(f"0x{timestamp}", 16)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


rprint("\n* ------- STATE --------- *")
rprint(f"State: {board}-{win_top}-{win_bottom}-{start}-{end}-{turn}-{player_turn}")
player_turn = int(player_turn)
rprint(
    f"Start: {timestamp_to_date(start)}\nEnd: {timestamp_to_date(end) if end != '00000000' else '-'}"
    f"\nTurn: {int(turn)}{'a' if player_turn == 1 else 'b'}"
    f"\n{'Player turn' if end == '00000000' else 'Winner'}: {player_turn}"
)


def print_board(board_str):
    grid = [list(board_str[i * 6 : (i + 1) * 6]) for i in range(6)]
    rprint("             ---   player 2")
    rprint("            |   |          ")
    rprint("  -------------------------")
    rprint(" y  0   1   2   3   4   5")
    rprint("x -------------------------")
    for i, row in enumerate(grid):
        rprint(f"{i} | {' | '.join(c if c != '0' else ' ' for c in row)} |")
    rprint("  -------------------------")
    rprint("            |   |          ")
    rprint("  player 1   ---           ")


print_board(board)
rprint("* ----------------------- *")
