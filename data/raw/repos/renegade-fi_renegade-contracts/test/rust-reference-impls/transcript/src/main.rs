use std::env;
use std::error::Error;

use ark_bn254::Bn254;
use ark_ec::pairing::Pairing;
use mpc_plonk::transcript::{PlonkTranscript, SolidityTranscript};
use renegade_constants::Scalar;

/// Type alias for the base field of the Bn254 curve
type BaseField = <Bn254 as Pairing>::BaseField;

fn main() -> Result<(), Box<dyn Error>> {
    // Skip the first argument (program name)
    let args: Vec<String> = env::args().skip(1).collect();
    if args.is_empty() {
        eprintln!("Expected at least 1 argument, got 0");
        std::process::exit(1);
    }

    // Create a single transcript instance to use for all inputs
    let mut ts = <SolidityTranscript as PlonkTranscript<BaseField>>::new(b"unused_label");
    let mut challenges = Vec::new();

    // For each argument, append it to the transcript and get a challenge
    for arg in args {
        // Parse the hex string
        let trimmed = arg.trim_start_matches("0x");
        let bytes = hex::decode(trimmed)?;

        // Append message and get challenge
        <SolidityTranscript as PlonkTranscript<BaseField>>::append_message(
            &mut ts,
            b"unused_label",
            &bytes,
        )?;
        let challenge =
            <SolidityTranscript as PlonkTranscript<BaseField>>::get_and_append_challenge::<Bn254>(
                &mut ts,
                b"unused_label",
            )?;

        // Convert challenge to scalar and store
        let scalar = Scalar::new(challenge);
        challenges.push(scalar);
    }

    // Convert challenges to decimal strings and join with spaces
    let challenge_strings: Vec<String> = challenges
        .iter()
        .map(|c| c.to_biguint().to_string())
        .collect();

    // Output results as space-separated values with RES: prefix
    println!("RES:{}", challenge_strings.join(" "));
    Ok(())
}
