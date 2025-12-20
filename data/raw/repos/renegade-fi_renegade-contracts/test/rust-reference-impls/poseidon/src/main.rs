use renegade_constants::Scalar;
use renegade_crypto::fields::scalar_to_biguint;
use renegade_crypto::hash::Poseidon2Sponge;
use std::env;

fn main() {
    let args: Vec<String> = env::args().collect();

    // Expect two arguments after the program name
    if args.len() < 3 {
        eprintln!("Usage: {} <input1> <input2>", args[0]);
        eprintln!("Expected 2 arguments, got {}", args.len() - 1);
        std::process::exit(1);
    }

    // Parse inputs as decimal strings into Scalars
    let fp1 = Scalar::from_decimal_string(&args[1]).unwrap();
    let fp2 = Scalar::from_decimal_string(&args[2]).unwrap();

    let mut sponge = Poseidon2Sponge::new();
    let res = sponge.hash(&[fp1.inner(), fp2.inner()]);
    let res_biguint = scalar_to_biguint(&Scalar::new(res));
    let res_hex = format!("{res_biguint:x}");

    // Print with a prefix we can strip, if we do not do this, the forge FFI interface
    // may interpret the output as raw bytes or a string, somewhat unpredictably
    println!("RES:0x{res_hex}");
}
