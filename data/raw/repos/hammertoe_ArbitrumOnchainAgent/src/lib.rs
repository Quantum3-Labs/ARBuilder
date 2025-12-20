// Allow `cargo stylus export-abi` to generate a main function.
#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
extern crate alloc;

/// Import items from the SDK. The prelude contains common traits and macros.
use stylus_sdk::{alloy_primitives::{Address, I32, U32, U256, FixedBytes}, prelude::*};
use stylus_sdk::{alloy_sol_types::sol, evm};

use stylus_sdk::storage::{StorageArray, StorageI32, StorageAddress, StorageU32};
use std::fmt::Write;
use std::fmt;


/// The maze is a fixed 5×5 grid.
const MAZE_SIZE: usize = 5;
/// Four possible actions.
const ACTION_COUNT: usize = 4;
/// The total number of cells in the maze.
const Q_TABLE_SIZE: usize = MAZE_SIZE * MAZE_SIZE * ACTION_COUNT;


/// The maze cell types.
#[derive(Copy, Clone, PartialEq)]
pub enum Cell {
    Empty,
    Wall,
    Start,
    Goal,
}

/// The maze layout is fixed at compile time.
pub const MAZE_LAYOUT: [[Cell; MAZE_SIZE]; MAZE_SIZE] = [
    [Cell::Start, Cell::Empty, Cell::Wall,  Cell::Empty, Cell::Empty],
    [Cell::Empty, Cell::Empty, Cell::Wall,  Cell::Empty, Cell::Wall],
    [Cell::Wall,  Cell::Empty, Cell::Empty, Cell::Empty, Cell::Empty],
    [Cell::Empty, Cell::Wall,  Cell::Wall,  Cell::Wall,  Cell::Empty],
    [Cell::Empty, Cell::Empty, Cell::Empty, Cell::Goal,  Cell::Empty],
];

/// The four possible actions.
#[derive(Copy, Clone)]
pub enum Action {
    Up,
    Down,
    Left,
    Right,
}

impl Action {
    /// Return an array of all actions.
    pub fn iterator() -> [Action; ACTION_COUNT] {
        [Action::Up, Action::Down, Action::Left, Action::Right]
    }
}

sol! {
    event TrainingCompleted();
}

#[entrypoint]

/// Our main storage struct.
#[storage]
pub struct Contract {
    /// The owner (if minted).
    owner: StorageAddress,
    /// The maze state (Q‑table).
    //q_table: StorageArray<StorageArray<StorageArray<StorageI32, ACTION_COUNT>, MAZE_SIZE>, MAZE_SIZE>,
    q_table: StorageArray<StorageI32, Q_TABLE_SIZE>,
    /// A counter used for RNG seeding.
    rng_seed: StorageU32,
}

/// Start of our contract public functions.
#[public]
impl Contract {

    pub fn supports_interface(&self, interface: FixedBytes<4>) -> bool {
        let interface_slice_array: [u8; 4] = interface.as_slice().try_into().unwrap();
        // Convert interface_id to u32 for easier comparison
        let id = u32::from_be_bytes(interface_slice_array);
        
        // Compare with known interface IDs
        id == 0x01ffc9a7 || // ERC-165
        id == 0x80ac58cd || // ERC-721
        id == 0x5b5e139f    // ERC-721Metadata
    }

    /// Mint the single token
    pub fn mint(&mut self, to: Address) {
        self.owner.set(to);
        self.rng_seed.set(U32::from(1));
    }

    pub fn symbol(&self) -> String {
        "QMAZE".to_string()
    }

    pub fn name(&self) -> String {
        "Q-Learning Maze NFT".to_string()
    }

    pub fn description(&self) -> String {
        "A maze solved using Q-learning algorithm. The arrows show the learned optimal path.".to_string()
    }

    pub fn balance_of(&self, owner: Address) -> U256 {
        if owner == self.owner.get() {
            U256::from(1)
        } else {
            U256::from(0)
        }
    }

    pub fn owner_of(&self, token_id: U256) -> Result<Address, Vec<u8>> {
        // Since we only have one token, check if token_id is 1
        if token_id != U256::from(1) {
            return Err("Invalid token ID".as_bytes().to_vec());
        }

        // Get the owner address
        let owner = self.owner.get();
        
        // Check if the token has been minted
        if owner == Address::ZERO {
            return Err("Token not minted".as_bytes().to_vec());
        }

        Ok(owner)
    }

    pub fn get_qtable(&self) -> [i32; Q_TABLE_SIZE] {
        let mut arr: [i32; Q_TABLE_SIZE] = [0; Q_TABLE_SIZE];
        for i in 0..Q_TABLE_SIZE {
            arr[i] = self.q_table.get(i).unwrap().as_i32();
        }
        arr
    }

    /// Train the Q‑table using integer arithmetic.
    ///
    /// `alpha` and `gamma` are given as percentages (0–100). The update rule is:
    ///
    /// ```text
    /// new_q = old_q + (alpha * (reward + (gamma * max_next)/100 - old_q))/100
    /// ```
    pub fn train(&mut self, episodes: u32, max_steps: u32, epsilon: u32, alpha: u32, gamma: u32) {
        let start = Self::get_start_position();
        let mut rng_seed = self.rng_seed.get().to::<u32>();
        for _ in 0..episodes {
            let mut pos = start;
            for _ in 0..max_steps {
                // Copy current cell's Q‑values.
//                let mut current_q = self.q_table.get(pos.0).unwrap().get(pos.1).unwrap() as Vec<i32>;
                let mut current_q = self.decode_q(pos.0, pos.1);
                let (action, new_seed) = Self::choose_action(&current_q, epsilon, rng_seed);
                rng_seed = new_seed;
                self.rng_seed.set(U32::from(new_seed));
                let next_pos = Self::next_state(pos.0, pos.1, action);
                let reward = Self::get_reward(next_pos.0, next_pos.1);
                let next_q = self.decode_q(next_pos.0, next_pos.1);
                let max_next = Self::max_q_value(&next_q);
                let a_index = match action {
                    Action::Up    => 0,
                    Action::Down  => 1,
                    Action::Left  => 2,
                    Action::Right => 3,
                };
                // Compute delta:
                // delta = reward + ( (gamma as i32 * max_next) / 100 ) - current_q[a_index]
                // Update this part in the train function
                let delta = reward * 1000 + (gamma as i32 * max_next) - current_q[a_index] * 100;
                // Q-learning update:
                // new_q = old_q + ((alpha as i32 * delta) / 100)
                current_q[a_index] = current_q[a_index] + ((alpha as i32 * delta) / 10000) as i32;
                // Write the updated Q‑values back.
                self.encode_q(pos.0, pos.1, current_q);
                pos = next_pos;
                if MAZE_LAYOUT[pos.0][pos.1] == Cell::Goal {
                    break; // end episode when goal is reached
                }
            }
        }
        evm::log(TrainingCompleted{});
    }

    /// Generate dynamic SVG metadata that visualizes the maze and overlays an arrow
    /// (indicating the best action) for each empty or start cell.
    ///
    /// Because no dynamic allocation is allowed, we write into a fixed-size global buffer.
    /// (This simple approach is not thread-safe but is acceptable for a workshop demo.)
    #[selector(name = "tokenURI")]
    pub fn token_uri(&self, token_id: U256) -> String {
        // Buffers for SVG and JSON
        static mut SVG_BUFFER: [u8; 8192] = [0; 8192];
        static mut JSON_BUFFER: [u8; 12288] = [0; 12288];

        // A simple fixed-size buffer writer
        struct BufferWriter {
            buf: &'static mut [u8],
            pos: usize,
        }

        impl BufferWriter {
            fn new(buf: &'static mut [u8]) -> Self {
                Self { buf, pos: 0 }
            }
        }

        impl Write for BufferWriter {
            fn write_str(&mut self, s: &str) -> fmt::Result {
                let bytes = s.as_bytes();
                if self.pos + bytes.len() > self.buf.len() {
                    return Err(fmt::Error);
                }
                for &b in bytes {
                    self.buf[self.pos] = b;
                    self.pos += 1;
                }
                Ok(())
            }
        }

        unsafe {
            let svg_buf = &mut SVG_BUFFER;
            let mut svg_writer = BufferWriter::new(svg_buf);

            // Calculate dimensions for a nicely sized SVG
            let cell_size = 320 / MAZE_SIZE as u32;
            let width = cell_size * MAZE_SIZE as u32;
            let height = cell_size * MAZE_SIZE as u32;
            
            // Write the SVG header
            let _ = write!(
                svg_writer,
                "<?xml version=\"1.0\" encoding=\"UTF-8\"?><svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{w}\" height=\"{h}\" viewBox=\"0 0 {w} {h}\">",
                w = width,
                h = height
            );

            // For each cell in the maze...
            for i in 0..MAZE_SIZE {
                for j in 0..MAZE_SIZE {
                    let x = j * cell_size as usize;
                    let y = i * cell_size as usize;
                    let fill = match MAZE_LAYOUT[i][j] {
                        Cell::Wall  => "black",
                        Cell::Start => "green",
                        Cell::Goal  => "red",
                        _          => "white",
                    };
                    let _ = write!(
                        svg_writer,
                        "<rect x=\"{x}\" y=\"{y}\" width=\"{s}\" height=\"{s}\" fill=\"{fill}\" stroke=\"gray\"/>",
                        x = x,
                        y = y,
                        s = cell_size,
                        fill = fill
                    );

                    // For Empty and Start cells, overlay an arrow indicating the best action
                    if MAZE_LAYOUT[i][j] == Cell::Empty || MAZE_LAYOUT[i][j] == Cell::Start {
                        let q_values = self.decode_q(i, j);
                        let mut best_index = 0;
                        let mut best_val = q_values[0];
                        for (k, &val) in q_values.iter().enumerate() {
                            if val > best_val {
                                best_val = val;
                                best_index = k;
                            }
                        }
                        let arrow = match best_index {
                            0 => "↑",
                            1 => "↓",
                            2 => "←",
                            3 => "→",
                            _ => "",
                        };
                        let text_x = x + (cell_size as usize / 2);
                        let text_y = y + (cell_size as usize / 2 + cell_size as usize / 6);
                        let font_size = cell_size / 2;
                        let _ = write!(
                            svg_writer,
                            "<text x=\"{x}\" y=\"{y}\" font-size=\"{fs}\" text-anchor=\"middle\" fill=\"blue\">{arrow}</text>",
                            x = text_x,
                            y = text_y,
                            fs = font_size,
                            arrow = arrow
                        );
                    }
                }
            }
            let _ = write!(svg_writer, "</svg>");

            // Get the final SVG string and base64 encode it
            let svg_pos = svg_writer.pos;
            drop(svg_writer);
            let svg_base64 = Self::base64_encode(&SVG_BUFFER[..svg_pos]);
            let svg_uri = format!("data:image/svg+xml;base64,{}", svg_base64);

            // Create the JSON metadata
            let json_buf = &mut JSON_BUFFER;
            let mut json_writer = BufferWriter::new(json_buf);
            
            let _ = write!(
                json_writer,
                "{{\"name\":\"Q-Learning Maze\",\"description\":\"An NFT of a maze with a path discovered through Q-learning reinforcement learning. Each arrow shows the optimal action learned for that position.\",\"image\":\"{}\"}}", 
                svg_uri
            );

            // Base64 encode the entire JSON and return as data URI
            let json_pos = json_writer.pos;
            drop(json_writer);
            let json_base64 = Self::base64_encode(&JSON_BUFFER[..json_pos]);
            
            format!("data:application/json;base64,{}", json_base64)
        }
    }
}

/// Start of our contract private functions.
impl Contract {
     /// Find the starting position in the maze.
    fn get_start_position() -> (usize, usize) {
        for i in 0..MAZE_SIZE {
            for j in 0..MAZE_SIZE {
                if MAZE_LAYOUT[i][j] == Cell::Start {
                    return (i, j);
                }
            }
        }
        (0, 0) // Fallback (should not occur)
    }

    /// Check if (x, y) is in bounds and not a wall.
    fn is_valid_position(x: isize, y: isize) -> bool {
        if x < 0 || y < 0 || (x as usize) >= MAZE_SIZE || (y as usize) >= MAZE_SIZE {
            return false;
        }
        MAZE_LAYOUT[x as usize][y as usize] != Cell::Wall
    }

    /// Compute the next state given a cell and an action.
    fn next_state(x: usize, y: usize, action: Action) -> (usize, usize) {
        let (dx, dy) = match action {
            Action::Up    => (-1, 0),
            Action::Down  => (1, 0),
            Action::Left  => (0, -1),
            Action::Right => (0, 1),
        };
        let new_x = x as isize + dx;
        let new_y = y as isize + dy;
        if Self::is_valid_position(new_x, new_y) {
            (new_x as usize, new_y as usize)
        } else {
            (x, y)
        }
    }

    /// Return a reward for entering (x, y). Goal gives 100; otherwise –1.
    pub fn get_reward(x: usize, y: usize) -> i32 {
        if MAZE_LAYOUT[x][y] == Cell::Goal {
            100
        } else {
            -1
        }
    }

    /// Return the maximum Q‑value from an array.
    pub fn max_q_value(q_values: &[i32; ACTION_COUNT]) -> i32 {
        let mut max = q_values[0];
        for &val in q_values.iter() {
            if val > max {
                max = val;
            }
        }
        max
    }

    /// A very simple pseudo‑random number generator using u32 arithmetic.
    /// Returns a value in [0, 100) and an updated seed.
    pub fn pseudo_random(seed: u32) -> (u32, u32) {
        // Use common constants.
        let a: u32 = 1664525;
        let c: u32 = 1013904223;
        let new_seed = seed.wrapping_mul(a).wrapping_add(c);
        let random = new_seed % 100;
        (random, new_seed)
    }


    pub fn decode_q(&self, x: usize, y: usize) -> [i32; ACTION_COUNT] {
        let mut arr: [i32; ACTION_COUNT] = [0; ACTION_COUNT];
        for i in 0..ACTION_COUNT {
            arr[i] = self.q_table.get(x * MAZE_SIZE * ACTION_COUNT + y * ACTION_COUNT + i).unwrap().as_i32();
        }
        arr
    }

    pub fn encode_q(&mut self, x: usize, y: usize, q_values: [i32; ACTION_COUNT]) {
        for i in 0..ACTION_COUNT {
            self.q_table.setter(x * MAZE_SIZE * ACTION_COUNT + y * ACTION_COUNT + i).unwrap().set(I32::unchecked_from(q_values[i]));
        }
    }

    /// Choose an action using an epsilon‑greedy policy.
    /// `epsilon` is given as a percentage (0–100).
    //pub fn choose_action(q_values: &[i32; ACTION_COUNT], epsilon: u32, seed: u32) -> (Action, u32) {
    //pub fn choose_action(q_values: &[i32; ACTION_COUNT], epsilon: u32, seed: u32) -> (Action, u32) {
    pub fn choose_action(q_values: &[i32; ACTION_COUNT], epsilon: u32, seed: u32) -> (Action, u32) {

        let (rand_val, new_seed) = Self::pseudo_random(seed);
        if rand_val < epsilon {
            // Choose a random action.
            let (rand_action, new_seed2) = Self::pseudo_random(new_seed);
            let index = (rand_action as usize) % ACTION_COUNT;
            let action = match index {
                0 => Action::Up,
                1 => Action::Down,
                2 => Action::Left,
                _ => Action::Right,
            };
            (action, new_seed2)
        } else {
            // Choose the best action.
            let mut best_action = Action::Up;
            let mut best_val = q_values[0];
            for (i, &val) in q_values.iter().enumerate() {
                if val > best_val {
                    best_val = val;
                    best_action = match i {
                        0 => Action::Up,
                        1 => Action::Down,
                        2 => Action::Left,
                        _ => Action::Right,
                    };
                }
            }
            (best_action, new_seed)
        }
    }

    // Base64 encoding helper function
    fn base64_encode(input: &[u8]) -> String {
        const ALPHABET: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
        let mut result = String::with_capacity((input.len() + 2) / 3 * 4);
        
        for chunk in input.chunks(3) {
            let b = match chunk.len() {
                3 => ((chunk[0] as u32) << 16) | ((chunk[1] as u32) << 8) | (chunk[2] as u32),
                2 => ((chunk[0] as u32) << 16) | ((chunk[1] as u32) << 8),
                1 => (chunk[0] as u32) << 16,
                _ => unreachable!(),
            };
            
            // Convert to base64 characters
            result.push(ALPHABET[(b >> 18 & 0x3F) as usize] as char);
            result.push(ALPHABET[(b >> 12 & 0x3F) as usize] as char);
            
            if chunk.len() > 1 {
                result.push(ALPHABET[(b >> 6 & 0x3F) as usize] as char);
            } else {
                result.push('=');
            }
            
            if chunk.len() > 2 {
                result.push(ALPHABET[(b & 0x3F) as usize] as char);
            } else {
                result.push('=');
            }
        }
        
        result
    }


}
