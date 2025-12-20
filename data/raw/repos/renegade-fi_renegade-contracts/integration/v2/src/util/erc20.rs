//! Mock ERC20 contract bindings

use alloy::{network::Ethereum, sol};

/// An ERC20 instance with default generics
pub type ERC20 = ERC20MockInstance<Wallet, Ethereum>;

sol! {
    #[sol(rpc)]
    interface ERC20Mock {
        function mint(address account, uint256 amount) external;
        function burn(address account, uint256 amount) external;
        function totalSupply() external view returns (uint256);
        function balanceOf(address account) external view returns (uint256);
        function transfer(address to, uint256 amount) external returns (bool);
        function allowance(address owner, address spender) external view returns (uint256);
        function approve(address spender, uint256 amount) external returns (bool);
        function transferFrom(address from, address to, uint256 amount) external returns (bool);
        function name() external view returns (string memory);
        function symbol() external view returns (string memory);
        function decimals() external view returns (uint8);

        #[derive(Debug, PartialEq, Eq)]
        event Transfer(address indexed from, address indexed to, uint256 value);
    }
}

pub use ERC20Mock::*;

use crate::util::darkpool::Wallet;
