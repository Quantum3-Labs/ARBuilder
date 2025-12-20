// Only run this as a WASM if the export-abi feature is not set.
#![cfg_attr(not(feature = "export-abi"), no_main)]
extern crate alloc;

/// Initializes a custom, global allocator for Rust programs compiled to WASM.
#[global_allocator]
static ALLOC: mini_alloc::MiniAlloc = mini_alloc::MiniAlloc::INIT;

use alloy_primitives::{Address, U8};
use chess_engine::{Board, BoardBuilder, Color, GameResult, Move, Piece, Position};

/// Import the Stylus SDK along with alloy primitive types for use in our program.
use stylus_sdk::{alloy_primitives::U256, console, msg, prelude::*};

/// Game Status
// const PENDING: u8 = 0;
const CONTINUING: u8 = 1;
const ILLEGAL_MOVE: u8 = 2;
const STALEMATE: u8 = 3;
const VICTORY: u8 = 4;

/// Colors
const WHITE: u8 = 0;
const BLACK: u8 = 1;

/// Piece types
const PAWN: u8 = 1;
const KNIGHT: u8 = 2;
const BISHOP: u8 = 3;
const ROOK: u8 = 4;
const QUEEN: u8 = 5;
const KING: u8 = 6;

/// Bit masks
const COLOR_MASK: u8 = 1;
const PIECE_TYPE_MASK: u8 = 7;

sol_storage! {
  #[entrypoint]
  pub struct StylusChess {
    /// Total games of chess started
    uint256 total_games;
    /// Used to store a single pending game while waiting for a player two to join.
    uint256 pending_game;
    /// Stores info for each chess game
    mapping(uint256 => GameInfo) games;
  }

  pub struct GameInfo {
    /// Player 1 is WHITE
    address player_one;
    /// Player 2 is BLACK
    address player_two;
    /// PENDING (waiting second player) = 0, CONTINUING = 1, STALEMATE = 3, or VICTORY = 4
    uint8 game_status;
    /// Player turn 0 = WHITE; 1 = BLACK
    uint8 turn_color;
    /// 0 = WHITE; 1 = BLACK
    uint8 victor;
    /// All the info needed to rebuild the board
    uint256 board_state;
  }
}

#[external]
impl StylusChess {
    /// Gets the game number from storage.
    pub fn total_games(&self) -> Result<U256, Vec<u8>> {
        Ok(U256::from(self.total_games.get()))
    }

    /// Get the color of the current player
    pub fn get_turn_color(&self, game_number: U256) -> Result<U256, Vec<u8>> {
        let game_info = self.games.get(game_number);
        let turn_color = game_info.turn_color.get();

        Ok(U256::from(turn_color))
    }

    /// Get the address of the current player
    pub fn get_current_player(&self, game_number: U256) -> Result<Address, Vec<u8>> {
        let game_info = self.games.get(game_number);
        let turn_color = game_info.turn_color.get();

        let player_address = match turn_color == U8::from(WHITE) {
            true => game_info.player_one.get(),
            false => game_info.player_two.get(),
        };

        Ok(player_address)
    }

    /// Play a Move
    pub fn play_move(
        &mut self,
        game_number: U256,
        from_row: U256,
        from_col: U256,
        to_row: U256,
        to_col: U256,
    ) -> Result<U256, Vec<u8>> {
        let board = self.get_board_from_game_number(game_number);
        let current_player = self.get_current_player_address(game_number, board);
        let game_data = self.games.get(game_number);

        // only allow the current player address to execute this call
        if msg::sender() != current_player {
            return Ok(U256::from(ILLEGAL_MOVE));
        }

        // don't continue if game is already over
        if game_data.game_status.get() != U8::from(CONTINUING) {
            return Ok(U256::from(ILLEGAL_MOVE));
        }

        let from_position = Position::new(from_row.to(), from_col.to());
        let to_position = Position::new(to_row.to(), to_col.to());
        let player_move = Move::Piece(from_position, to_position);
        let move_result = board.play_move(player_move);

        let response = match move_result {
            GameResult::Continuing(new_board) => {
                let new_board_state = self.serialize_board(new_board);
                let mut game_setter = self.games.setter(game_number);
                game_setter.board_state.set(new_board_state);

                match new_board.get_turn_color() {
                    Color::White => {
                        game_setter.turn_color.set(U8::from(WHITE));
                    }
                    Color::Black => {
                        game_setter.turn_color.set(U8::from(BLACK));
                    }
                }

                U256::from(CONTINUING)
            }
            GameResult::Victory(_) => {
                let current_color = match board.get_turn_color() {
                    Color::White => U8::from(WHITE),
                    Color::Black => U8::from(BLACK),
                };
                let mut game_setter = self.games.setter(game_number);
                game_setter.victor.set(current_color);
                game_setter.game_status.set(U8::from(VICTORY));

                U256::from(VICTORY)
            }
            GameResult::Stalemate => {
                let mut game_setter = self.games.setter(game_number);
                game_setter.game_status.set(U8::from(STALEMATE));

                U256::from(STALEMATE)
            }
            _ => U256::from(ILLEGAL_MOVE),
        };

        Ok(response)
    }

    pub fn print_game_state(&self, game_number: U256) -> Result<(), Vec<u8>> {
        let game_info = self.games.get(U256::from(game_number));
        let board_state = game_info.board_state.get();
        let board: Board = self.deserialize_board(board_state);
        self.print_board(&board);

        Ok(())
    }

    /// The board layout for a particular game
    pub fn board_state_by_game_number(&self, game_number: U256) -> Result<U256, Vec<u8>> {
        let game_info = self.games.get(game_number);
        Ok(game_info.board_state.get())
    }

    /// Either creates a new game or joins a pending game if it exists
    /// Returns the game number
    pub fn create_or_join(&mut self) -> Result<U256, Vec<u8>> {
        let pending_game = self.pending_game.get();

        // Sets pending_game number and initializes a new board
        if pending_game == U256::from(0) {
            let game_number = self.get_next_game_number();
            self.pending_game.set(game_number);
            self.create_game(game_number);
            return Ok(U256::from(game_number));
        }

        self.join_game(pending_game);

        Ok(U256::from(pending_game))
    }
}

impl StylusChess {
    pub fn get_current_player_address(&self, game_number: U256, current_board: Board) -> Address {
        let game_info = self.games.get(game_number);
        match current_board.get_turn_color() {
            Color::White => game_info.player_one.get(),
            Color::Black => game_info.player_two.get(),
        }
    }

    fn get_board_from_game_number(&self, game_number: U256) -> Board {
        let game_info = self.games.get(game_number);
        let color = game_info.turn_color.get();
        let board_state = game_info.board_state.get();
        let board = self.deserialize_board(board_state);

        let color_enum = match color == U8::from(WHITE) {
            true => Color::White,
            false => Color::Black,
        };

        board.set_turn(color_enum)
    }

    fn get_next_game_number(&mut self) -> U256 {
        let game_number = self.total_games.get() + U256::from(1);
        self.total_games.set(game_number);
        game_number
    }

    fn create_game(&mut self, game_number: U256) {
        let board = Board::default();
        // Set up pieces for serialization
        let board_state = self.serialize_board(board);

        let mut game_info = self.games.setter(game_number);
        game_info.player_one.set(msg::sender());
        game_info.board_state.set(board_state);
    }

    fn join_game(&mut self, game_number: U256) {
        let mut game_info = self.games.setter(game_number);
        // join as player two
        game_info.player_two.set(msg::sender());
        // change status to continuing
        game_info.game_status.set(U8::from(CONTINUING));
        // empty out pending_game
        self.pending_game.set(U256::ZERO);
    }

    fn deserialize_board(&self, board_state: U256) -> Board {
        let mut board_builder: BoardBuilder = BoardBuilder::default();
        board_builder = board_builder.enable_castling();

        for row in 0..8_u8 {
            for col in 0..8_u8 {
                let base_offset: usize = ((row * 8 + col) * 4).into();
                let color_offset: usize = base_offset + 3;
                let piece_type_offset: usize = base_offset;

                let color = (board_state >> color_offset) & U256::from(COLOR_MASK);
                let piece_type = (board_state >> piece_type_offset) & U256::from(PIECE_TYPE_MASK);

                if piece_type != U256::ZERO {
                    let position = Position::new(row.into(), col.into());
                    let color_enum = match U8::from(color).to() {
                        WHITE => Color::White,
                        _ => Color::Black,
                    };
                    let piece = match U8::from(piece_type).to() {
                        KNIGHT => Piece::Knight(color_enum, position),
                        BISHOP => Piece::Bishop(color_enum, position),
                        ROOK => Piece::Rook(color_enum, position),
                        QUEEN => Piece::Queen(color_enum, position),
                        KING => Piece::King(color_enum, position),
                        _ => Piece::Pawn(color_enum, position),
                    };

                    board_builder = board_builder.piece(piece);
                }
            }
        }

        board_builder.build()
    }

    fn serialize_board(&self, board: Board) -> U256 {
        let mut board_state = U256::from(0);

        for row in 0..8_u8 {
            for col in 0..8_u8 {
                let position = Position::new(row.into(), col.into());
                let base_offset: usize = ((row * 8 + col) * 4).into();
                let color_offset: usize = base_offset + 3;
                let piece_type_offset: usize = base_offset;

                if let Some(board_piece) = board.get_piece(position) {
                    let color = if board_piece.get_color() == Color::White {
                        WHITE
                    } else {
                        BLACK
                    };

                    let piece_type = match board_piece {
                        Piece::Pawn(_, _) => PAWN,
                        Piece::Knight(_, _) => KNIGHT,
                        Piece::Bishop(_, _) => BISHOP,
                        Piece::Rook(_, _) => ROOK,
                        Piece::Queen(_, _) => QUEEN,
                        Piece::King(_, _) => KING,
                    };

                    board_state |= U256::from(color) << color_offset;
                    board_state |= U256::from(piece_type) << piece_type_offset;
                } else {
                    board_state |= U256::from(0) << (base_offset + 4);
                }
            }
        }

        board_state
    }

    fn print_board(&self, board: &Board) {
        let turn = board.get_turn_color();
        let abc = if turn == Color::White {
            "abcdefgh"
        } else {
            "hgfedcba"
        };

        console!("   {}", abc);
        console!("  ╔════════╗");
        let mut square_color = !turn;
        let height = 8;
        let width = 8;

        for row in 0..height {
            let print_row = match turn {
                Color::White => height - row - 1,
                Color::Black => row,
            };
            let mut row_text = String::new();
            let row_label = format!("{} ║", print_row + 1);
            row_text.push_str(row_label.as_str());

            for col in 0..width {
                let print_col = match turn {
                    Color::Black => width - col - 1,
                    Color::White => col,
                };

                let pos = Position::new(print_row, print_col);

                let s = if let Some(piece) = board.get_piece(pos) {
                    piece.to_string()
                } else {
                    String::from(match square_color {
                        Color::White => "░",
                        Color::Black => "▓",
                    })
                };
                if Some(pos) == board.get_en_passant() {
                    row_text.push_str(format!("\x1b[34m{}\x1b[m\x1b[0m", s).as_str());
                } else if board.is_threatened(pos, turn) {
                    row_text.push_str(format!("\x1b[31m{}\x1b[m\x1b[0m", s).as_str());
                } else if board.is_threatened(pos, !turn) {
                    row_text.push_str(format!("\x1b[32m{}\x1b[m\x1b[0m", s).as_str());
                } else {
                    row_text.push_str(s.as_str());
                }

                square_color = !square_color;
            }
            row_text.push('║');
            console!("{}", row_text);

            square_color = !square_color;
        }

        console!("  ╚════════╝");
        console!("   {}", abc);
    }
}
