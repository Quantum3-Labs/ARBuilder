//! Utilities for sending and waiting on transactions

use std::time::Duration;

use alloy::{
    contract::{CallBuilder, CallDecoder, Error as ContractError},
    network::Ethereum,
    providers::{DynProvider, Provider},
    rpc::types::TransactionReceipt,
    transports::TransportError,
};
use eyre::Result;
use renegade_abi::v2::IDarkpoolV2;
use test_helpers::assert_eq_result;

/// The call builder type for the tests
pub type TestCallBuilder<'a, C> = CallBuilder<&'a DynProvider, C, Ethereum>;

// ----------------
// | Transactions |
// ----------------

/// Wait for a transaction receipt and ensure it was successful
pub async fn wait_for_tx_success<C: CallDecoder>(
    tx: TestCallBuilder<'_, C>,
) -> Result<TransactionReceipt> {
    let receipt = send_tx(tx).await?;
    assert_eq_result!(receipt.status(), true)?;
    Ok(receipt)
}

/// Send a transaction and wait for it to succeed or fail
pub async fn send_tx<C: CallDecoder>(tx: TestCallBuilder<'_, C>) -> Result<TransactionReceipt> {
    let pending_tx_res = tx.send().await;
    let pending_tx = match pending_tx_res {
        Ok(pending_tx) => pending_tx,
        Err(ContractError::TransportError(TransportError::ErrorResp(err_payload))) => {
            let decoded =
                err_payload.as_decoded_interface_error::<IDarkpoolV2::IDarkpoolV2Errors>();

            let err_str = decoded.map(|e| format!("{e:?}")).unwrap_or_else(|| {
                let msg = err_payload.message;
                let data = err_payload.data.unwrap_or_default();
                format!("unknown error: {msg} (data = {data})")
            });
            eyre::bail!("pending tx error: {err_str}");
        }
        Err(err) => {
            println!("pending tx error: {err:?}");
            return Err(eyre::eyre!("pending tx error: {err:?}"));
        }
    };

    let tx_hash = *pending_tx.tx_hash();

    // Retry fetching the receipt up to 10 times
    // The current version of alloy has issues watching the pending transaction directly, so we patch this here
    let mut remaining_attempts = 10;
    let provider = tx.provider;
    while remaining_attempts > 0 {
        match provider.get_transaction_receipt(tx_hash).await? {
            Some(receipt) => return Ok(receipt),
            None => {
                tokio::time::sleep(Duration::from_millis(100)).await;
                remaining_attempts -= 1;
            }
        }
    }

    eyre::bail!("no tx receipt found after retries");
}
