//! Test utilities

pub mod deployments;
pub mod merkle;
pub mod transactions;

use eyre::Result;

// ---------------
// | Error Utils |
// ---------------

/// A trait with auto-implementation that makes it easier to convert errors to `eyre::Result`
pub trait WrapEyre {
    /// The type of the value being wrapped
    type Value;

    /// Convert the error to an eyre::Result
    fn to_eyre(self) -> Result<Self::Value>;
}

impl<R, E: ToString> WrapEyre for core::result::Result<R, E> {
    type Value = R;

    fn to_eyre(self) -> Result<R> {
        match self {
            Ok(r) => Ok(r),
            Err(e) => Err(eyre::eyre!(e.to_string())),
        }
    }
}
