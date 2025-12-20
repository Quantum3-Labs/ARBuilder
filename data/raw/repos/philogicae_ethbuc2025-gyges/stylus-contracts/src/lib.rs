#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
extern crate alloc;

use alloy_primitives::*;
use alloy_sol_types::sol;
use stylus_sdk::prelude::*;
use stylus_sdk::stylus_core::log;

sol_storage! {
    #[entrypoint]
    pub struct Gyges {
        uint256 nb_games;
        mapping(uint256 => Game) games;
        mapping(address => Player) players;
        mapping(string => address) usernames;
    }

    pub struct Game { // by id
        address player_one;
        address player_two;
        bytes32 state; // bytes: 6x6-board=18, winning-cells=2, start=4, end=4, turn=3, player-turn=1
    }

    pub struct Player { // by address
        string username;
        uint256 nb_games;
        uint256 nb_wins;
        mapping(uint256 => uint256) game_ids;
    }
}

sol! {
    event Created(uint256 game_id, address player_one, address player_two);
    event Played(uint256 game_id, address player, uint256[] action);
    error InvalidOperation(string message);
}

#[derive(SolidityError)]
pub enum GygesError {
    InvalidOperation(InvalidOperation),
}

#[public]
impl Gyges {
    pub fn register_username(&mut self, username: String) -> Result<(), GygesError> {
        if self.usernames.getter(username.clone()).get() != Address::new([0; 20]) {
            return Err(GygesError::InvalidOperation(InvalidOperation {
                message: "User already exists".to_string(),
            }));
        }
        let sender = self.vm().msg_sender();
        self.usernames.setter(username.clone()).set(sender);
        self.players
            .setter(sender)
            .username
            .set_str(username.clone());
        Ok(())
    }

    pub fn get_address_by_username(&self, username: String) -> Address {
        self.usernames.get(username)
    }

    pub fn get_player_by_address(&self, address: Address) -> (String, U256, U256, Vec<U256>) {
        let player = self.players.get(address);
        let nb_games = player.nb_games.get();
        let mut games = Vec::new();
        if nb_games > U256::ZERO {
            for i in 0..nb_games.try_into().unwrap() {
                let game_id = player.game_ids.get(U256::from(i));
                games.push(game_id);
            }
        }
        (
            player.username.get_string(),
            nb_games,
            player.nb_wins.get(),
            games,
        )
    }

    pub fn get_player_by_username(&self, username: String) -> (Address, U256, U256, Vec<U256>) {
        let address = self.get_address_by_username(username);
        let player = self.get_player_by_address(address);
        (address, player.1, player.2, player.3)
    }

    pub fn new_game(&mut self, opponent: String) -> Result<(), GygesError> {
        let sender = self.vm().msg_sender();
        if self.players.get(sender).username.get_string() == "" {
            return Err(GygesError::InvalidOperation(InvalidOperation {
                message: "Register first".to_string(),
            }));
        }
        let opponent_addr = self.get_address_by_username(opponent.clone());
        if opponent_addr == Address::new([0; 20]) {
            return Err(GygesError::InvalidOperation(InvalidOperation {
                message: "Opponent not found".to_string(),
            }));
        }
        if opponent_addr == sender {
            return Err(GygesError::InvalidOperation(InvalidOperation {
                message: "Cannot play against yourself".to_string(),
            }));
        }

        let game_id = self.nb_games.get();
        let new_board = self.gen_new_board();

        // Gyges layout
        self.nb_games.set(game_id.wrapping_add(U256::from(1)));

        // Game layout
        let mut new_game = self.games.setter(game_id);
        new_game.player_one.set(sender);
        new_game.player_two.set(opponent_addr);
        new_game.state.set(new_board);

        // Player 1 layout
        let player_one_nbg = self.players.get(sender).nb_games.get();
        let mut player_one = self.players.setter(sender);
        player_one
            .nb_games
            .set(player_one_nbg.wrapping_add(U256::from(1)));
        player_one.game_ids.setter(player_one_nbg).set(game_id);

        // Player 2 layout
        let player_two_nbg = self.players.get(opponent_addr).nb_games.get();
        let mut player_two = self.players.setter(opponent_addr);
        player_two
            .nb_games
            .set(player_two_nbg.wrapping_add(U256::from(1)));
        player_two.game_ids.setter(player_two_nbg).set(game_id);

        log(
            self.vm(),
            Created {
                game_id,
                player_one: sender,
                player_two: opponent_addr,
            },
        );
        Ok(())
    }

    pub fn game_by_id(&self, game_id: U256) -> (Address, Address, FixedBytes<32>) {
        let game = self.games.get(game_id);
        (
            game.player_one.get(),
            game.player_two.get(),
            game.state.get(),
        )
    }

    pub fn play(&mut self, action: Vec<U256>) -> Result<(), GygesError> {
        /* Action encoding example (each step = 3 values)
         * action[0..3] = [start_x, start_y, game_id]
         * action[3..6] = [cell_x, cell_y, 1]: Busy cell -> choose(1)='jump'
         * action[6..9] = [cell_x, cell_y, 2]: Busy cell -> choose(2)='replace'
         * action[9..12] = [end_x, end_y, 0]: Free cell -> End of turn
         *
         * Ending example:
         * ...
         * action[9..12] = [end_x, end_y, 2]: Free cell at (step-1) -> choose(3)='win'
         * */

        let action = action.to_vec();
        let game_id: U256 = action[2];
        let sender = self.vm().msg_sender();
        let game = self.games.get(game_id);
        let is_player_one = game.player_one.get() == sender;
        let is_player_two = game.player_two.get() == sender;
        if !(is_player_one || is_player_two) {
            return Err(GygesError::InvalidOperation(InvalidOperation {
                message: "Not your game".to_string(),
            }));
        }
        let state_bytes = game.state.get();
        let state = state_bytes.as_slice();
        if state[24..28] != [0; 4] {
            return Err(GygesError::InvalidOperation(InvalidOperation {
                message: "Game already terminated".to_string(),
            }));
        }
        if (is_player_one && state[31] != 1) || (is_player_two && state[31] != 2) {
            return Err(GygesError::InvalidOperation(InvalidOperation {
                message: "Not your turn".to_string(),
            }));
        }

        // Checks selection
        let mut x: usize = action[0].try_into().unwrap();
        let mut y: usize = action[1].try_into().unwrap();
        let cell_idx = x * 6 + y;
        let (piece, alt_piece, is_first_piece) = if cell_idx % 2 == 0 {
            (state[cell_idx / 2] >> 4, state[cell_idx / 2] & 15, true)
        } else {
            (state[cell_idx / 2] & 15, state[cell_idx / 2] >> 4, false)
        };
        if !(x < 6
            && y < 6
            && piece > 0
            && if is_player_two {
                x == 0 || state[0..(x * 6) / 2].iter().all(|&b| b == 0)
            } else {
                x == 5 || state[(x * 6) / 2..18].iter().all(|&b| b == 0)
            })
        {
            return Err(GygesError::InvalidOperation(InvalidOperation {
                message: "Invalid piece selected".to_string(),
            }));
        }

        // Perform moves
        let mut new_state = state.to_vec();
        let mut jump_power: u8 = 0; // Power of the future jump (1)
        let mut saved_piece: u8 = 0; // Saved piece for future placement (2)
        let mut fly: usize = 0; // Save loop-index for future placement (2)
        for i in 1..action.len() / 3 {
            // Check valid pos diff
            let new_x: usize = action[i * 3].try_into().unwrap();
            let new_y: usize = action[i * 3 + 1].try_into().unwrap();
            let dist = self.manhattan_distance([x, y], [new_x, new_y]);
            if !(new_x < 6
                && new_y < 6
                && match if jump_power > 0 {
                    let tmp = jump_power;
                    jump_power = 0;
                    tmp
                } else {
                    piece
                } {
                    1..=2 => true,
                    3 => dist % 2 == 1,
                    _ => false,
                })
            {
                return Err(GygesError::InvalidOperation(InvalidOperation {
                    message: "Invalid move".to_string(),
                }));
            }

            // Load new pos from board
            let cell_idx_new = new_x * 6 + new_y;
            let (cell, alt_cell, is_first_cell) = if cell_idx_new % 2 == 0 {
                (
                    new_state[cell_idx_new / 2] >> 4,
                    new_state[cell_idx_new / 2] & 15,
                    true,
                )
            } else {
                (
                    new_state[cell_idx_new / 2] & 15,
                    new_state[cell_idx_new / 2] >> 4,
                    false,
                )
            };

            // Empty destination -> End of turn
            if cell == 0 {
                new_state[cell_idx / 2] = if is_first_piece {
                    alt_piece
                } else {
                    alt_piece << 4
                };
                new_state[cell_idx_new / 2] = if is_first_cell {
                    piece << 4 | alt_cell
                } else {
                    alt_cell << 4 | piece
                };
                break;
            // Occupied destination -> Jump or Replace?
            } else {
                let choice: usize = action[i * 3 + 2].try_into().unwrap();
                match choice {
                    // Jump
                    1 => {
                        jump_power = cell;
                        x = new_x;
                        y = new_y;
                        continue;
                    }
                    // Replace
                    2 => {
                        fly = i + 1 as usize;
                        saved_piece = cell;
                        // Move piece to new cell
                        new_state[cell_idx / 2] = if is_first_piece {
                            alt_piece
                        } else {
                            alt_piece << 4
                        };
                        new_state[cell_idx_new / 2] = if is_first_cell {
                            piece << 4 | alt_cell
                        } else {
                            alt_cell << 4 | piece
                        };
                        break;
                    }
                    _ => {
                        return Err(GygesError::InvalidOperation(InvalidOperation {
                            message: "Only jump=1 & replace=2 are allowed".to_string(),
                        }));
                    }
                }
            }
        }

        // Check for safe landing after jump
        if jump_power > 0 {
            return Err(GygesError::InvalidOperation(InvalidOperation {
                message: "Incomplete jump".to_string(),
            }));
        }

        // If replacement was used
        if fly > 0 {
            let new_x: usize = action[fly * 3].try_into().unwrap();
            let new_y: usize = action[fly * 3 + 1].try_into().unwrap();

            // Load new pos from board
            let cell_idx_new = new_x * 6 + new_y;
            let (cell, alt_cell, is_first_cell) = if cell_idx_new % 2 == 0 {
                (
                    new_state[cell_idx_new / 2] >> 4,
                    new_state[cell_idx_new / 2] & 15,
                    true,
                )
            } else {
                (
                    new_state[cell_idx_new / 2] & 15,
                    new_state[cell_idx_new / 2] >> 4,
                    false,
                )
            };

            // Place it if valid
            if new_x < 6 && new_y < 6 && cell == 0 {
                // TODO: Check placement not behind opponent zone
                new_state[cell_idx_new / 2] = if is_first_cell {
                    saved_piece << 4 | alt_cell
                } else {
                    alt_cell << 4 | saved_piece
                };
            } else {
                return Err(GygesError::InvalidOperation(InvalidOperation {
                    message: "Invalid placement".to_string(),
                }));
            }
        }

        // TODO: Check win condition

        // Update new state
        if is_player_one {
            // Same turn, but next move is for player 2
            new_state[31] = 2
        } else {
            // Copy previous turn value and increment by 1
            let turn =
                ((new_state[28] as u32) << 16 | (new_state[29] as u32) << 8 | new_state[30] as u32)
                    + 1;
            new_state[28] = ((turn >> 16) & 0xFF) as u8;
            new_state[29] = ((turn >> 8) & 0xFF) as u8;
            new_state[30] = (turn & 0xFF) as u8;
            // New turn, next move is for player 1
            new_state[31] = 1
        };
        self.games
            .setter(game_id)
            .state
            .set(FixedBytes::from_slice(&new_state));

        log(
            self.vm(),
            Played {
                game_id,
                player: sender,
                action,
            },
        );
        Ok(())
    }
}

// Private methods
impl Gyges {
    // Linear congruential generator for pseudo-random numbers
    pub fn lcg_step(&self, seed: &mut u64) -> u64 {
        let a: u64 = 1664525;
        let c: u64 = 1013904223;
        *seed = seed.wrapping_mul(a).wrapping_add(c); // ranqd1
        *seed
    }

    pub fn shuffle<T>(&self, slice: &mut [T], seed: &mut u64) {
        for i in (1..6).rev() {
            let random_val = self.lcg_step(seed);
            let j = (random_val % (i as u64 + 1)) as usize;
            slice.swap(i, j);
        }
    }

    pub fn gen_new_board(&self) -> FixedBytes<32> {
        let timestamp = self.vm().block_timestamp();
        let mut seed = timestamp;
        let mut first_row: [u8; 6] = [1, 2, 3, 1, 2, 3];
        let mut last_row: [u8; 6] = [3, 2, 1, 3, 2, 1];

        self.shuffle(&mut first_row, &mut seed);
        self.shuffle(&mut last_row, &mut seed);

        // Game state on a single bytes32
        FixedBytes::<32>::from_slice(
            [
                vec![
                    (first_row[0] << 4) | first_row[1],
                    (first_row[2] << 4) | first_row[3],
                    (first_row[4] << 4) | first_row[5],
                ], // 1 row (3 bytes)
                [0; 12].to_vec(), // 4 empty rows (12 bytes)
                vec![
                    (last_row[0] << 4) | last_row[1],
                    (last_row[2] << 4) | last_row[3],
                    (last_row[4] << 4) | last_row[5],
                ], // 1 row (3 bytes)
                [0; 2].to_vec(),  // winning cells at top/bottom (2x1 byte)
                timestamp.to_be_bytes()[4..].to_vec(), // start (4 bytes)
                [0, 0, 0, 0, 0, 0, 1, 1].to_vec(), // end=null (4 bytes) + turn=1 (3 bytes) + player-turn=1 (1 byte)
            ]
            .concat()
            .as_slice(),
        )
    }

    pub fn manhattan_distance(&self, from: [usize; 2], to: [usize; 2]) -> u8 {
        ((from[0] as i8 - to[0] as i8).abs() + (from[1] as i8 - to[1] as i8).abs()) as u8
    }
}

/* #[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn test_gyges() {
        use stylus_sdk::testing::*;
        let vm = TestVM::default();
        let mut _contract = Gyges::from(&vm);
        // assert_eq!(U256::ZERO, contract.number());
    }
} */
