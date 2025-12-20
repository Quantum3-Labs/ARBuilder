use alloy::{network::Ethereum, sol};

use crate::util::darkpool::Wallet;

sol! {
    #[sol(rpc)]
    interface IPermit2 {
        function allowance(address user, address token, address spender)
            external
            view
            returns (uint160 amount, uint48 expiration, uint48 nonce);

        function approve(address token, address spender, uint160 amount, uint48 expiration) external;

        function transferFrom(address from, address to, uint160 amount, address token) external;

        function invalidateNonces(address token, address spender, uint48 newNonce) external;
    }
}

pub use IPermit2::*;

pub type Permit2 = IPermit2Instance<Wallet, Ethereum>;
