"""
generate_stylus_code MCP Tool.

Generates Stylus/Rust smart contract code based on user requirements.
Uses verified working templates as the foundation to ensure compilable output.

Key improvement: Instead of generating from scratch, this tool customizes
curated templates from official Stylus examples.
"""

import logging
import re
from typing import Optional

from .base import BaseTool
from .get_stylus_context import GetStylusContextTool

logger = logging.getLogger(__name__)

TEMPLATE_DISCLAIMER = (
    "This generated code is a starting entrypoint — a working foundation for you to build upon. "
    "Review, customize, and extend it to match your specific requirements before deploying."
)

# Import templates
try:
    from src.templates.stylus_templates import (
        StylusTemplate,
        get_template,
        select_template,
    )

    HAS_TEMPLATES = True
except ImportError:
    HAS_TEMPLATES = False
    StylusTemplate = None
    select_template = None
    get_template = None

# Import compiler verifier - handle gracefully if not available
try:
    from src.utils.compiler_verifier import (
        CompilerVerifier,
        format_errors_for_llm,
        format_fix_guidance,
    )

    HAS_COMPILER = True
except ImportError:
    HAS_COMPILER = False
    CompilerVerifier = None

# Import version manager - handle gracefully if not available
try:
    from src.utils.version_manager import (
        _to_major_minor,
        apply_version_transforms,
        detect_version_from_cargo_toml,
        get_alloy_primitives_version,
        get_alloy_sol_types_version,
        get_deprecation_warning,
        get_main_version,
        get_minimum_version,
        get_version_patterns,
        is_at_least_010,
        is_version_deprecated,
    )

    HAS_VERSION_MANAGER = True
except ImportError:
    HAS_VERSION_MANAGER = False

    # Last-resort fallbacks when version_manager is unavailable.
    # Source of truth: shared/stylus-versions.json → src/utils/version_manager.py
    def get_main_version():
        return "0.10.0"

    def get_minimum_version():
        return "0.8.0"

    def is_version_deprecated(v):
        return False

    def get_version_patterns(v):
        return {
            "attributes": ["#[public]"],
            "error_handling": "Result<T, Vec<u8>>",
            "cfg_attr": '#![cfg_attr(not(feature = "export-abi"), no_main)]',
            "sender": "self.vm().msg_sender()",
        }

    def get_alloy_primitives_version(v):
        return "1.0.1"

    def get_alloy_sol_types_version(v):
        return "1.0.1"

    def detect_version_from_cargo_toml(c):
        return None

    def get_deprecation_warning(v):
        return None

    def apply_version_transforms(code, from_v, to_v):
        return code

    def _to_major_minor(v):
        return ".".join(v.split(".")[:2])

    def is_at_least_010(v):
        return True


# ── Shared compilation rules (deduped from both system prompts) ──
# Plain Python string — NOT an f-string. Use regular { } for literal braces.

STYLUS_COMPILATION_RULES = """\
STORAGE ACCESS:
- ALWAYS use .get() to read storage: `self.field.get()` NOT `self.field`.
- ALWAYS use .set(val) to write: `self.field.set(val)`.
- For mappings: read with `self.map.get(key)`, write with `self.map.setter(key).set(val)`.
- .setter(key) is ONLY for mappings. For simple fields (uint256, address, bool), \
use `self.field.set(val)` directly — NOT `self.field.setter().set(val)` or \
`self.field.setter(val).set(val)`.
- NESTED MAPPINGS: `mapping(a => mapping(b => c))` — read with `self.map.get(key1).get(key2)`, \
write by chaining `.setter()` calls: `self.map.setter(k1).setter(k2).set(v)`. \
Do NOT use tuple keys `(k1, k2)`. \
Do NOT mix `.get()` or `.getter()` then `.setter()` — both return immutable refs \
conflicting with `.setter()`'s mutable borrow. ALWAYS chain .setter() for writes.
- MAPPING READS RETURN VALUES DIRECTLY: `StorageMap::get(key)` returns the value \
type directly (zero-default for uninitialized), NOT `Option`. Do NOT call \
`.unwrap_or_default()` on mapping reads.
- Do NOT use `.getter(key).get_string()` except for `mapping(... => string)`. \
Do NOT add extra `.get()` after mapping reads — `.get(key)` already returns the value.
- DYNAMIC ARRAYS: In sol_storage!, declare as `uint256[] items;`. Append with \
`self.items.push(val)` for primitives, `self.items.grow()` for structs. \
Do NOT use `.setter(len).unwrap()`.
- StorageVec API: `len()` returns `usize` (NOT U256). Use `usize` for loop indices. \
`setter(i)` returns `Option` — call `.unwrap()` before `.set()`. \
`getter(i)` also returns `Option` — call `.unwrap()`. \
To convert U256 to usize: `index.to::<usize>()`. Do NOT use `.as_usize()`. \
`.as_u64()`, `.as_u32()`, `.as_u128()` also do NOT exist — use `.to::<u64>()`, `.to::<u32>()`, `.to::<u128>()`.
- BORROW CHECKER: Extract values to local vars before combining storage reads and writes: \
`let sender = self.vm().msg_sender(); self.balances.setter(sender).set(amount);`
- StorageString: Use `.set_str("value")` to write and `.get_string()` to read. \
Do NOT use `.set()` or `.get()` on string storage fields.
- STORAGESTRING VIEW FUNCTIONS: When returning a `string` field from sol_storage! \
in a view function, ALWAYS call `.get_string()`: \
`pub fn name(&self) -> String { self.name.get_string() }`. \
NEVER return `self.name` directly — it is `StorageString`, not `String`. \
Do NOT use `.push_str()` on StorageString — extract first: \
`let s = self.name.get_string(); format!("{}{}", s, other)`.
- STRING MAPPING READS: `mapping(... => string)` — Use `.getter(key).get_string()` to \
read — returns `String`. Do NOT call `.get_string()` again on the result. \
Write: `.setter(key).set_str("val")`.
- STRING MAPPING WRITES: `.setter(key).set_str(value)` — call `.set_str()` DIRECTLY \
on the `StorageGuardMut<StorageString>` returned by `.setter(key)`. \
WRONG: `.setter(key).setter().set_str(value)`. CORRECT: `.setter(key).set_str(value)`.
- MUTABLE BINDINGS: `.setter()` result stored in a variable needs `let mut` if \
methods are called on it.

IMPORTS AND no_std:
- ALWAYS include `use alloc::vec;` (the module) alongside `use alloc::vec::Vec;` — \
sol_storage! needs it.
- STRING IMPORTS: When using `String`, add `use alloc::string::String;`. When using \
`.to_string()`, ALSO add `use alloc::string::ToString;`. NOT in prelude in no_std.
- NO STD LIBRARY: Do NOT use `std::time`, `std::collections`, `std::io`, or any std library. \
For timestamps use `self.vm().block_timestamp()`.
- Call IMPORT: `Call` is available from `prelude::*` — do NOT add \
`use stylus_sdk::call::Call;` separately.

EXTERNAL INTERFACES:
- Use `sol_interface!` (NOT `sol!`) for external contract interfaces. \
`sol!` is ONLY for events and errors. Writing `sol! { interface IToken { ... } }` \
generates an EVENT, not a callable interface.
- CROSS-CONTRACT CALLS: VIEW calls: `ifoo.method(self.vm(), Call::new(), args)?`. \
STATE-MODIFYING calls: extract Call first: `let call = Call::new_mutating(self);` \
then `ifoo.method(self.vm(), call, args)?` — avoids borrow checker conflicts.
- External calls require `&mut self` (NOT `&self` — view functions revert).
- sol_interface! HOST ARGUMENT: `self.vm()` MUST be the FIRST argument, followed \
by Call context, then Solidity parameters. \
Example: `token.transfer(self.vm(), call, to, amount)?;` \
NOT `token.transfer(call, to, amount)?;`.
- sol_interface! GENERATES SNAKE_CASE METHODS: `transferFrom` -> `.transfer_from()`, \
`balanceOf` -> `.balance_of()`. NEVER use camelCase in Rust sol_interface! calls.

TYPES:
- sol_storage! TYPES: Use SOLIDITY syntax inside sol_storage!: `uint256`, `address`, \
`bool`, `string`, `mapping(...)`, `type[]`. NOT Rust Storage* types like `StorageU256`, \
`StorageString`, etc.
- sol_storage! SYNTAX: Fields are type + name + semicolon ONLY. NO default values: \
`uint256 value;` NOT `uint256 value = 0;`. NO Rust types.
- U8 TYPE: `uint8` -> `U8` (Uint<8,1>), not native u8. Set: `U8::from(18u8)`. \
Read: `.to::<u8>()`.
- B256 IS NOT Uint: B256 is `FixedBytes<32>`, NOT `Uint<256>`. \
`B256::from_uint()` and `B256::from_limbs()` do NOT exist. \
Use `B256::from(value.to_be_bytes::<32>())`. \
For limbs: `B256::from(U256::from_limbs([1, 0, 0, 0]).to_be_bytes::<32>())`. \
Use `B256::ZERO` for zero, `B256::with_last_byte(n)` for small values.
- CONST U256: `U256::from()` is NOT const-compatible. Use `U256::from_limbs([N, 0, 0, 0])`. \
`U256::ZERO` is fine (it's already a const).
- ZERO CONSTANTS: Use `U256::ZERO`, `Address::ZERO`, `U128::ZERO` (uppercase const). \
NOT `U256::zero()` or `Address::zero()` — these functions do not exist.
- ADDRESS ARRAY READS: `*self.list.get(idx).unwrap()` on `address[]` dereferences to \
`FixedBytes<20>`, NOT `Address`. Convert: `Address::from(*self.list.get(idx).unwrap())`.
- SolidityError ENUM: Each variant MUST wrap a DISTINCT error type. Two variants wrapping \
the same type cause conflicting `From` impls.
- unwrap_or vs unwrap_or_else: `.unwrap_or(VALUE)` for values. \
`.unwrap_or_else(|| VALUE)` for closures.

EVENTS AND ERRORS:
- sol! MACRO IMPORT: When using sol! for events or errors, MUST explicitly import: \
`use alloy_sol_types::{sol, SolError};`. sol! is NOT available from prelude::*.
- sol! EVENT/ERROR FIELDS: Use camelCase (Solidity convention): `tokenId` NOT `token_id`.
- sol! STRUCT INIT: ALWAYS use explicit `field: value` syntax. \
WRONG: `CapExceeded { newCap }` (shorthand — no local `newCap` exists). \
CORRECT: `CapExceeded { newCap: new_cap }`. NEVER use Rust shorthand for sol! structs \
because field names are camelCase but Rust variables are snake_case.
- abi_encode() ON ERRORS: `.abi_encode()` is on the inner `sol!` error struct \
(SolError trait), NOT on the `#[derive(SolidityError)]` enum wrapper. \
WRONG: `MyErrors::NotOwner(NotOwner{...}).abi_encode()`. \
CORRECT: `NotOwner{caller, owner}.abi_encode()`.
- sol! ERROR/EVENT TYPE MATCHING: Solidity field types MUST match the Rust values \
passed. `address` -> Address, `uint256` -> U256. If passing U256, the field MUST be \
`uint256`, NOT `address`. Comparison errors (InsufficientBalance, InsufficientStake) — \
ALL value fields should be `uint256`.
- EVENT/ERROR NAMING: Never give an event and error the same name — they generate \
conflicting Rust structs.
- DUPLICATE DEFINITIONS: Put all errors in one `sol! { }` block. Never define \
the same name twice.
- vm().log() returns `()` — do NOT use `?` after it.
- NO Debug DERIVE WITH SolidityError: sol! types do NOT implement Debug. \
NEVER write `#[derive(SolidityError, Debug)]` — use `#[derive(SolidityError)]` only.

SDK API (0.10.0):
- TRANSFER ETH: `use stylus_sdk::call::transfer::transfer_eth;` then \
`transfer_eth(self.vm(), to, amount)?;`. NOT `self.transfer_eth()`.
- Use `self.vm().msg_sender()` for caller (NOT `msg::sender()`).
- Use `self.vm().msg_value()` for sent ETH (NOT `msg::value()`).
- Use `self.vm().log(Event { ... })` to emit events (NOT `evm::log`).
- CONTRACT ADDRESS: `self.vm().contract_address()` NOT `self.vm().address()`.
- BLOCK TIMESTAMP: `self.vm().block_timestamp()` returns `u64`. Wrap with \
`U256::from()` before storing in uint256 fields.
- RESULT PROPAGATION: Always use `?` to propagate `Result` from helper methods.
- Do NOT use `use stylus_sdk::evm` or `use stylus_sdk::msg` — removed in 0.10.0.
- ABI EXPORTS: Stylus exports snake_case Rust fn names as camelCase in the ABI.

PROJECT STRUCTURE:
- Package name in Cargo.toml MUST use underscores (e.g., "my_contract").
- src/main.rs is REQUIRED — uses `print_from_args()` (NOT `print_abi()`).
- crate-type = ["lib", "cdylib"] — "lib" needed for bin target linking.
- Stylus.toml with [workspace], [workspace.networks], and [contract] sections.
- rust-toolchain.toml with channel = "1.91.0".

OUTPUT:
- NO CONST IN #[public] IMPL: Move constants to module level BEFORE the impl block.
- NO UNDERSCORE-PREFIXED FN IN #[public] IMPL: Put internal helpers in a SEPARATE \
`impl MyContract { ... }` block WITHOUT `#[public]`.
- CLEAN OUTPUT: Output ONLY valid Rust code. NEVER include natural language \
commentary or corrections inside code blocks.
- INTERNAL HELPERS — NO PHANTOM VARIABLES: Internal check functions must get ALL \
data from storage or parameters. NEVER write `let role = role;`."""

STYLUS_REFERENCE_CODE = """\
ETH transfer (withdraw/deposit/send ETH):
```rust
use stylus_sdk::call::transfer::transfer_eth;

pub fn withdraw(&mut self, to: Address, amount: U256) -> Result<(), Vec<u8>> {
    transfer_eth(self.vm(), to, amount)?;
    Ok(())
}
```

Cross-contract VIEW call (read-only — Call::new() is fine):
```rust
sol_interface! {
    interface IPriceFeed {
        function latestPrice() external view returns (uint256);
    }
}

pub fn get_price(&mut self, feed_addr: Address) -> Result<U256, Vec<u8>> {
    let feed = IPriceFeed::new(feed_addr);
    let price = feed.latest_price(self.vm(), Call::new())?;
    Ok(price)
}
```

Cross-contract state-modifying call (extract Call to avoid borrow conflict):
```rust
sol_interface! {
    interface IToken {
        function transfer(address to, uint256 amount) external returns (bool);
    }
}

pub fn transfer_tokens(
    &mut self, token: Address, to: Address, amount: U256,
) -> Result<bool, Vec<u8>> {
    let tok = IToken::new(token);
    let call = Call::new_mutating(self);
    let success = tok.transfer(self.vm(), call, to, amount)?;
    Ok(success)
}
```

Storage access patterns:
```rust
// Simple field: .get() to read, .set() to write
let val = self.balance.get();
self.balance.set(val + U256::from(1));

// Mapping: .get(key) to read, .setter(key).set(val) to write
let bal = self.balances.get(user);
self.balances.setter(user).set(new_bal);

// Nested mapping: chain .setter() for writes
self.allowances.setter(owner).setter(spender).set(amount);
let allowance = self.allowances.getter(owner).get(spender);
```

Dynamic array (append to sol_storage! array):
```rust
// In sol_storage!: uint256[] items;
// Append primitive:
self.items.push(new_val);
// For structs: let mut entry = self.items.grow(); entry.field.set(val);
```"""


def get_system_prompt(target_version: str) -> str:
    """Generate version-aware system prompt."""
    patterns = get_version_patterns(target_version)
    alloy_version = get_alloy_primitives_version(target_version)
    main_attr = patterns.get("attributes", ["#[public]"])[0]
    error_handling = patterns.get("error_handling", "Result<T, Vec<u8>>")
    cfg_attr = patterns.get("cfg_attr", '#![cfg_attr(not(feature = "export-abi"), no_main)]')

    sender_pattern = patterns.get("sender", "self.vm().msg_sender()")

    return f"""You are an expert Stylus smart contract \
developer. You write high-quality Rust code for \
Arbitrum Stylus contracts.

Target SDK Version: stylus-sdk {target_version}

Key Stylus patterns for v{target_version}:
1. Use `sol_storage!` macro for state storage
2. Use `#[entrypoint]` on the main contract struct
3. Use `{main_attr}` for public functions
4. Use `{sender_pattern}` to get the caller address
5. Handle errors with {error_handling}
6. Include {cfg_attr}
7. Follow Rust naming conventions \
(snake_case for functions, PascalCase for types)

Dependencies for v{target_version}:
- stylus-sdk = "{target_version}"
- alloy-primitives = "{alloy_version}"

Required project files (SDK 0.10.0+):
- Stylus.toml with [workspace], \
[workspace.networks], and [contract] sections
- rust-toolchain.toml with channel = "1.91.0"
- src/main.rs with print_from_args() for ABI export

{STYLUS_COMPILATION_RULES}

When generating code:
- Generate complete, compilable Rust code
- Include all necessary imports incl. `use alloc::vec;`
- Add helpful comments for complex logic
- Use proper error handling
- Follow security best practices \
(check for overflows, validate inputs)
"""


# Legacy prompt for backwards compatibility
SYSTEM_PROMPT = get_system_prompt(get_main_version())


def get_template_system_prompt(template: "StylusTemplate", target_version: str) -> str:
    """Generate system prompt for template-based generation."""
    alloy_version = get_alloy_primitives_version(target_version)

    return f"""You are an expert Stylus (Rust) smart \
contract developer for Arbitrum.

CRITICAL: You are customizing a WORKING template. \
The template below compiles and deploys correctly.
Your job is to MODIFY this template to match the \
user's requirements while keeping the EXACT \
structure intact.

Base Template: {template.name}
Template Description: {template.description}
Template Features: {", ".join(template.features)}

Target SDK Version: stylus-sdk {target_version}
Alloy Primitives: {alloy_version}

ABSOLUTE RULES - NEVER VIOLATE THESE:
1. KEEP the EXACT first 4 lines: #![cfg_attr...], \
#![cfg_attr...], #[macro_use], extern crate alloc;
2. KEEP all use statements from the template - \
you may ADD more but NEVER remove
3. There must be EXACTLY ONE sol_storage! block - \
NEVER create empty sol_storage! blocks
4. KEEP the #[entrypoint] attribute in sol_storage!
5. KEEP the #[public] attribute on the impl block
6. When using sol! for events or errors, you MUST \
explicitly import it: \
`use alloy_sol_types::{{sol, SolError}};` — \
sol! is NOT available from prelude::*. \
If only using events (no .abi_encode()), \
`use alloy_sol_types::sol;` is sufficient.
7. If adding events/errors with sol! macro, they \
must be BEFORE sol_storage!
7b. EVERY event emitted with self.vm().log(EventName {{ ... }}) \
MUST be declared in a sol! block. If the template declares \
Transfer and Approval events but you add/keep an approve() \
function that emits Approval, you MUST keep the Approval event \
declaration. Undeclared events cause compile errors.
8. KEEP the Cargo.toml [profile.release] section \
exactly as provided

{STYLUS_COMPILATION_RULES}

WHAT YOU MAY DO:
- Rename the contract struct in sol_storage! to \
match the user's request
- Add/modify storage fields inside sol_storage!
- Add/modify functions inside the #[public] impl
- Add events using \
sol! {{ event EventName(...); }} BEFORE sol_storage!
- Add error types using \
sol! {{ error ErrorName(...); }} BEFORE sol_storage!
- Add internal helper functions (without #[public])
- Define external contract interfaces with \
sol_interface! (NOT sol!) for cross-contract calls

IMPORTS - USE THESE PATTERNS:
- Types from \
stylus_sdk::alloy_primitives::{{Address, U256, ...}}
- sol! macro: use alloy_sol_types::sol; \
(NOT from prelude)
- For events: \
self.vm().log(EventName {{ field1, field2 }}) \
(NOT evm::log)
- For caller: self.vm().msg_sender() \
(NOT msg::sender())
- For ETH transfers: \
`use stylus_sdk::call::transfer::transfer_eth;` \
then `transfer_eth(self.vm(), to, amount)?;`
- For errors: \
return Err(ErrorName {{ ... }}.abi_encode()) \
— requires use alloy_sol_types::SolError;
- For cross-contract calls: define with \
sol_interface! {{ interface IFoo {{ \
function bar(address) external returns (uint256); \
}} }}
- VIEW call: `ifoo.bar(self.vm(), Call::new(), addr)?`
- STATE-MODIFYING call: `let call = Call::new_mutating(self); ifoo.bar(self.vm(), call, args)?`
- External calls require &mut self (NOT &self — view functions revert on external calls)
- Do NOT use stylus_sdk::evm (removed in 0.10.0) or stylus_sdk::msg

REFERENCE CODE — copy these EXACTLY when the user's request needs them:

{STYLUS_REFERENCE_CODE}

Output format:
1. Brief explanation of changes (1-2 sentences)
2. Complete lib.rs in a ```rust code block

IMPORTANT: Do NOT output Cargo.toml - the template's Cargo.toml will be used as-is."""


# Legacy templates for backwards compatibility (when templates module not available)
CONTRACT_TEMPLATES = {
    "erc20": """use stylus_sdk::prelude::*;
use stylus_sdk::alloy_primitives::{Address, U256};


sol_storage! {
    #[entrypoint]
    pub struct Token {
        mapping(address => uint256) balances;
        mapping(address => mapping(address => uint256)) allowances;
        uint256 total_supply;
    }
}

#[public]
impl Token {
    // ERC20 implementation
}
""",
    "erc721": """use stylus_sdk::prelude::*;
use stylus_sdk::alloy_primitives::{Address, U256};


sol_storage! {
    #[entrypoint]
    pub struct NFT {
        mapping(uint256 => address) owners;
        mapping(address => uint256) balances;
        mapping(uint256 => address) token_approvals;
        mapping(address => mapping(address => bool)) operator_approvals;
        uint256 next_token_id;
    }
}

#[public]
impl NFT {
    // ERC721 implementation
}
""",
}


class GenerateStylusCodeTool(BaseTool):
    """
    Generates Stylus smart contract code.

    Uses RAG context to inform code generation with relevant examples.
    """

    MAX_COMPILE_ATTEMPTS = 3

    def __init__(
        self,
        context_tool: Optional[GetStylusContextTool] = None,
        compiler_verifier: Optional["CompilerVerifier"] = None,
        **kwargs,
    ):
        """
        Initialize the tool.

        Args:
            context_tool: GetStylusContextTool for retrieving examples.
            compiler_verifier: Optional CompilerVerifier for Docker-based cargo check.
        """
        super().__init__(**kwargs)
        self.context_tool = context_tool or GetStylusContextTool(**kwargs)
        if compiler_verifier is not None:
            self.compiler = compiler_verifier
        elif HAS_COMPILER and CompilerVerifier is not None:
            self.compiler = CompilerVerifier()
        else:
            self.compiler = None

    def execute(
        self,
        prompt: str,
        context_query: Optional[str] = None,
        contract_type: Optional[str] = None,
        include_tests: bool = False,
        temperature: float = 0.2,
        target_version: Optional[str] = None,
        cargo_toml: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """
        Generate Stylus smart contract code using template-based generation.

        Args:
            prompt: Description of the code to generate.
            context_query: Optional query to retrieve context.
            contract_type: Type of contract (token, defi, utility, custom).
            include_tests: Whether to include unit tests.
            temperature: Generation temperature (0-1).
            target_version: Target stylus-sdk version (default: main version).
            cargo_toml: Optional Cargo.toml content for automatic version detection.

        Returns:
            Dict with code, cargo_toml, explanation, dependencies, warnings,
            context_used, target_version, template_used.
        """
        # Validate input
        if not prompt or not prompt.strip():
            return {"error": "Prompt is required and cannot be empty"}

        prompt = prompt.strip()
        warnings = []

        # Version detection/selection logic
        if cargo_toml:
            detected_version = detect_version_from_cargo_toml(cargo_toml)
            if detected_version:
                target_version = detected_version
                deprecation_warning = get_deprecation_warning(detected_version)
                if deprecation_warning:
                    warnings.append(deprecation_warning)

        # Default to main version if not specified
        if not target_version:
            target_version = get_main_version()

        try:
            # Select appropriate template (version-aware)
            template = None
            template_name = "legacy"

            if HAS_TEMPLATES and select_template:
                template = select_template(
                    contract_type or "utility", prompt, target_version=target_version
                )
                template_name = template.name

            # Retrieve relevant context for additional patterns
            context_used = []
            context_text = ""

            query = context_query or prompt
            context_result = self.context_tool.execute(
                query=query,
                n_results=3,  # Reduced since we have a template as base
                content_type="code",
                rerank=True,
                category_boosts=None,  # Use default Stylus-focused boosts
                target_version=target_version,
            )

            if "contexts" in context_result:
                for ctx in context_result["contexts"]:
                    context_used.append(
                        {
                            "source": ctx["source"],
                            "relevance": ctx["relevance_score"],
                        }
                    )
                    context_text += (
                        f"\n--- Example from {ctx['source']} ---\n{ctx['content'][:1500]}\n"
                    )

            # Build generation prompt
            if template:
                # Use template-based generation
                user_prompt = self._build_template_prompt(
                    prompt=prompt,
                    template=template,
                    context_text=context_text,
                    include_tests=include_tests,
                )
                system_prompt = get_template_system_prompt(template, target_version)
            else:
                # Fallback to legacy generation
                user_prompt = self._build_prompt(
                    prompt=prompt,
                    contract_type=contract_type,
                    context_text=context_text,
                    include_tests=include_tests,
                )
                system_prompt = get_system_prompt(target_version)

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = self._call_llm(
                messages=messages,
                temperature=temperature,
                max_tokens=8192,  # Allow longer output for complete contracts
            )

            # Parse response
            code, cargo_toml_output, explanation = self._parse_template_response(
                response, template, target_version=target_version
            )

            # Compile-verify-fix loop (if Docker available)
            compile_verified = False
            compile_attempts = 0

            if self.compiler and self.compiler.is_available() and cargo_toml_output:
                for attempt in range(self.MAX_COMPILE_ATTEMPTS):
                    compile_attempts = attempt + 1
                    logger.info(f"Compile check attempt {compile_attempts}")

                    result = self.compiler.verify(code, cargo_toml_output)

                    if result.skipped:
                        logger.info(f"Compile check skipped: {result.skip_reason}")
                        break

                    if result.success:
                        compile_verified = True
                        logger.info("Compile check passed")
                        break

                    # Build fix prompt with structured errors
                    actual_errors = [e for e in result.errors if e.level == "error"]
                    if not actual_errors:
                        compile_verified = True
                        break

                    error_text = format_errors_for_llm(actual_errors, code)
                    guidance = format_fix_guidance(actual_errors)
                    fix_prompt = self._build_fix_prompt(code, error_text, guidance)

                    fix_messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": fix_prompt},
                    ]

                    fix_response = self._call_llm(
                        messages=fix_messages,
                        temperature=0.1,
                        max_tokens=8192,
                    )

                    # Parse fixed code
                    fixed_code, _, _ = self._parse_template_response(fix_response, template)
                    if fixed_code and fixed_code != code:
                        code = fixed_code
                    else:
                        warnings.append(
                            f"Compile fix attempt {compile_attempts} did not produce different code"
                        )
                        break

            # Extract dependencies with correct versions
            dependencies = self._extract_dependencies(code, target_version)

            # Validate code
            validation_warnings = self._validate_code(code)
            warnings.extend(validation_warnings)

            # Derive project name from prompt and fix Cargo.toml/main.rs references
            # Only include 0.10.0-specific files when targeting 0.10.x+
            target_mm = _to_major_minor(target_version)  # noqa: F841
            main_rs_output = (
                (template.main_rs if template else "") if is_at_least_010(target_version) else ""
            )
            stylus_toml_output = (
                (template.stylus_toml if template else "")
                if is_at_least_010(target_version)
                else ""
            )
            rust_toolchain_toml_output = (
                (template.rust_toolchain_toml if template else "")
                if is_at_least_010(target_version)
                else ""
            )

            if cargo_toml_output:
                project_name = self._derive_project_name(prompt)
                # Fix package name (use underscores for cargo-stylus compatibility)
                cargo_toml_output = re.sub(
                    r'name\s*=\s*"[^"]+"',
                    f'name = "{project_name}"',
                    cargo_toml_output,
                )
                # Fix main.rs crate reference (print_from_args uses crate name)
                if main_rs_output:
                    main_rs_output = re.sub(
                        r"(\w+)::print_from_args\b",
                        f"{project_name}::print_from_args",
                        main_rs_output,
                    )

            return {
                "code": code,
                "cargo_toml": cargo_toml_output,
                "main_rs": main_rs_output,
                "stylus_toml": stylus_toml_output,
                "rust_toolchain_toml": rust_toolchain_toml_output,
                "explanation": explanation,
                "dependencies": dependencies,
                "warnings": warnings if warnings else [],
                "context_used": context_used,
                "target_version": target_version,
                "template_used": template_name,
                "compile_verified": compile_verified,
                "compile_attempts": compile_attempts,
                "disclaimer": TEMPLATE_DISCLAIMER,
            }

        except Exception as e:
            return {"error": f"Code generation failed: {str(e)}"}

    def _build_template_prompt(
        self,
        prompt: str,
        template: "StylusTemplate",
        context_text: str,
        include_tests: bool,
    ) -> str:
        """Build prompt for template-based generation."""
        parts = [
            "BASE TEMPLATE (lib.rs):",
            f"```rust\n{template.lib_rs}\n```",
            "",
            "BASE TEMPLATE (Cargo.toml):",
            f"```toml\n{template.cargo_toml}\n```",
            "",
        ]

        if context_text:
            parts.append("ADDITIONAL PATTERNS FROM DOCUMENTATION:")
            parts.append(context_text)
            parts.append("")

        parts.append("USER REQUEST:")
        parts.append(prompt)
        parts.append("")

        if include_tests:
            parts.append(
                "Keep the #[cfg(test)] module and update the tests to match the new functionality."
            )
        else:
            parts.append("You may remove the #[cfg(test)] module if not needed.")

        parts.append("")
        parts.append(
            "Please customize the template to implement"
            " the user's request."
            " Keep the working structure intact."
        )

        return "\n".join(parts)

    def _build_prompt(
        self,
        prompt: str,
        contract_type: Optional[str],
        context_text: str,
        include_tests: bool,
    ) -> str:
        """Build the generation prompt (legacy fallback)."""
        parts = []

        # Add template hint if contract type specified
        if contract_type and contract_type in CONTRACT_TEMPLATES:
            parts.append(
                f"Base your implementation on this {contract_type.upper()} template structure:"
            )
            parts.append(f"```rust\n{CONTRACT_TEMPLATES[contract_type]}\n```")
            parts.append("")

        # Add context if available
        if context_text:
            parts.append("Here are some relevant code examples for reference:")
            parts.append(context_text)
            parts.append("")

        # Add main request
        parts.append("Generate Stylus smart contract code for the following requirement:")
        parts.append(f"\n{prompt}\n")

        # Add test request if needed
        if include_tests:
            parts.append(
                "\nAlso include unit tests for the main"
                " functionality using Rust's"
                " #[test] attribute."
            )

        parts.append("\nProvide:")
        parts.append("1. Complete, compilable Rust code with all imports")
        parts.append("2. A brief explanation of the implementation")
        parts.append(
            "\nFormat your response with the code in a"
            " ```rust code block, followed by"
            " an explanation."
        )

        return "\n".join(parts)

    def _parse_response(self, response: str) -> tuple[str, str]:
        """Parse code and explanation from LLM response (legacy)."""
        code = ""
        explanation = ""

        # Extract code blocks
        code_pattern = r"```(?:rust)?\s*([\s\S]*?)```"
        matches = re.findall(code_pattern, response)

        if matches:
            # Combine all code blocks
            code = "\n\n".join(match.strip() for match in matches)

            # Get explanation (text after last code block)
            last_block_end = response.rfind("```")
            if last_block_end != -1:
                explanation = response[last_block_end + 3 :].strip()

        if not code:
            # No code blocks found, treat whole response as code
            code = response.strip()

        if not explanation:
            explanation = "Generated Stylus smart contract code based on the provided requirements."

        return code, explanation

    def _parse_template_response(
        self,
        response: str,
        template: Optional["StylusTemplate"],
        target_version: Optional[str] = None,
    ) -> tuple[str, str, str]:
        """Parse code, cargo.toml, and explanation from template-based response."""
        code = ""
        cargo_toml = ""
        explanation = ""

        # Extract rust code blocks
        rust_pattern = r"```rust\s*([\s\S]*?)```"
        rust_matches = re.findall(rust_pattern, response)

        if rust_matches:
            code = rust_matches[0].strip()

        # ALWAYS use template's Cargo.toml - don't trust LLM-generated Cargo.toml
        # LLM often makes typos (alloy-sol_types) or misses deps (ruint)
        if template:
            cargo_toml = template.cargo_toml

        # Extract explanation (text before first code block or after last)
        explanation_parts = response.split("```")
        if explanation_parts:
            # First part before any code block
            first_part = explanation_parts[0].strip()
            if first_part:
                explanation = first_part
            elif len(explanation_parts) > 1:
                # Try last part after all code blocks
                last_part = explanation_parts[-1].strip()
                if last_part:
                    explanation = last_part

        if not code:
            code = response.strip()

        if not explanation:
            explanation = "Contract customized based on your requirements."

        # Apply fixes for common LLM mistakes in code only
        # Cargo.toml comes directly from template, no fixes needed
        code = self._fix_code(code, template, target_version=target_version or get_main_version())

        return code, cargo_toml, explanation

    def _extract_dependencies(self, code: str, target_version: str) -> list[dict]:
        """Extract Cargo dependencies from code with correct versions for target SDK."""
        dependencies = []

        # Get version-appropriate dependency versions
        alloy_primitives_ver = get_alloy_primitives_version(target_version)
        alloy_sol_types_ver = get_alloy_sol_types_version(target_version)

        # Check for common Stylus dependencies
        if "stylus_sdk" in code or "stylus-sdk" in code:
            dependencies.append(
                {
                    "name": "stylus-sdk",
                    "version": target_version,
                }
            )

        if "alloy_primitives" in code or "alloy-primitives" in code:
            dependencies.append(
                {
                    "name": "alloy-primitives",
                    "version": alloy_primitives_ver,
                }
            )

        if "alloy_sol_types" in code or "alloy-sol-types" in code:
            dependencies.append(
                {
                    "name": "alloy-sol-types",
                    "version": alloy_sol_types_ver,
                }
            )

        return dependencies

    def _validate_code(self, code: str) -> list[str]:
        """Validate generated code and return warnings."""
        warnings = []

        # Check for basic Stylus patterns
        if "sol_storage!" not in code:
            warnings.append("Code may be missing sol_storage! macro for state storage")

        if "#[entrypoint]" not in code:
            warnings.append("Code may be missing #[entrypoint] attribute")

        # Check for balanced braces
        if code.count("{") != code.count("}"):
            warnings.append("Unbalanced curly braces detected")

        if code.count("(") != code.count(")"):
            warnings.append("Unbalanced parentheses detected")

        # Check for common security issues
        if "- " in code and "checked_sub" not in code.lower():
            warnings.append("Potential unchecked subtraction - consider using checked_sub")

        return warnings

    @staticmethod
    def _sanitize_sol_storage(code: str, template: Optional["StylusTemplate"]) -> str:
        """Structurally sanitize the sol_storage! block.

        Parses line-by-line inside the block and:
        - Strips `= value` default assignments (invalid in sol_storage!)
        - Removes garbled/empty lines (`;`, `= = ;`, etc.)
        - Validates each field matches known Solidity-in-Rust type patterns
        - Falls back to template's sol_storage! if the block is unsalvageable

        Returns the code with a cleaned sol_storage! block.
        """
        # Find the sol_storage! block
        m = re.search(r"(sol_storage!\s*\{)", code)
        if not m:
            return code

        block_start = m.start()
        brace_start = code.index("{", m.start())

        # Find matching closing brace
        depth = 0
        i = brace_start
        while i < len(code):
            if code[i] == "{":
                depth += 1
            elif code[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1

        if depth != 0:
            # Unbalanced — fall back to template if available
            if template:
                tmpl_m = re.search(
                    r"sol_storage!\s*\{[\s\S]*?\n\}", template.lib_rs
                )
                if tmpl_m:
                    return code[:block_start] + tmpl_m.group(0) + code[i + 1 :]
            return code

        block_end = i + 1
        block_content = code[brace_start + 1 : i]  # inside outer braces

        # Valid Solidity-in-Rust field type patterns for sol_storage!
        # Types: uint256, address, bool, string, bytes32, mapping(...), type[]
        valid_type_re = re.compile(
            r"^\s*(?:"
            r"(?:u?int(?:8|16|32|64|128|256))"  # uint256, int128, etc.
            r"|address"
            r"|bool"
            r"|string"
            r"|bytes\d*"  # bytes, bytes32, etc.
            r"|mapping\(.*\)"  # mapping(...)
            r"|[\w]+\[\]"  # dynamic arrays: uint256[], address[]
            r")\s+\w+\s*;$"
        )

        # Known structural lines (not field declarations)
        structural_re = re.compile(  # noqa: F841
            r"^\s*(?:"
            r"#\[entrypoint\]"
            r"|pub\s+struct\s+\w+"
            r"|\{|\}"
            r"|///.*"  # doc comments
            r"|//.*"  # comments
            r")$"
        )

        # Process the block's struct content
        # Find the inner struct braces
        struct_m = re.search(r"pub\s+struct\s+\w+\s*\{", block_content)
        if not struct_m:
            # No struct found — severely garbled, use template
            if template:
                tmpl_m = re.search(
                    r"sol_storage!\s*\{[\s\S]*?\n\}", template.lib_rs
                )
                if tmpl_m:
                    return code[:block_start] + tmpl_m.group(0) + code[block_end:]
            return code

        # Split into pre-struct and struct content
        struct_brace = block_content.index("{", struct_m.start())
        struct_depth = 0
        j = struct_brace
        while j < len(block_content):
            if block_content[j] == "{":
                struct_depth += 1
            elif block_content[j] == "}":
                struct_depth -= 1
                if struct_depth == 0:
                    break
            j += 1

        struct_inner = block_content[struct_brace + 1 : j]
        lines = struct_inner.split("\n")
        clean_lines = []
        garbled_count = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Allow comments
            if stripped.startswith("//"):
                clean_lines.append(line)
                continue

            # Strip default value assignments: `uint256 x = 0;` → `uint256 x;`
            # Use negative lookahead (?!>) to avoid matching `=>` in mappings
            cleaned = re.sub(
                r"(\w+)\s*=\s*(?!>)[^;]*;", r"\1;", stripped
            )

            # Remove pure garbage lines (only punctuation, no type keyword)
            if re.match(r"^[;=\s\[\]0-9,]+$", cleaned):
                garbled_count += 1
                continue

            # Validate it looks like a field declaration
            if valid_type_re.match(cleaned):
                # Reconstruct with proper indentation
                clean_lines.append(f"        {cleaned}")
            elif re.match(r"^\s*mapping\(", cleaned):
                # Mapping that might have complex nesting — keep but clean
                cleaned = re.sub(r"\s*=\s*(?!>)[^;]*;", ";", cleaned)
                if cleaned.endswith(";"):
                    clean_lines.append(f"        {cleaned}")
                else:
                    garbled_count += 1
            else:
                garbled_count += 1

        # If more than half the lines were garbled, fall back to template
        total_lines = len(lines) - lines.count("")
        if total_lines > 0 and garbled_count > total_lines / 2 and template:
            tmpl_m = re.search(
                r"sol_storage!\s*\{[\s\S]*?\n\}", template.lib_rs
            )
            if tmpl_m:
                return code[:block_start] + tmpl_m.group(0) + code[block_end:]

        # Check for missing fields: scan code for self.xxx.get/set/setter
        # references and ensure each has a declaration in sol_storage!
        # Extract field names from cleaned lines — any `type fieldname;` pattern.
        # Use a simple approach: the last word before `;` is the field name.
        declared_fields: set[str] = set()
        for cl in clean_lines:
            cl_stripped = cl.strip()
            if cl_stripped.startswith("//"):
                continue
            fname_m = re.search(r"(\w+)\s*;$", cl_stripped)
            if fname_m:
                declared_fields.add(fname_m.group(1))
        # Find self.xxx references outside sol_storage! block
        rest_of_code = code[block_end:]
        referenced_fields = set(
            re.findall(r"self\.(\w+)\s*\.(?:get|set|setter|getter|push|len|grow)\b",
                        rest_of_code)
        )
        # Exclude known non-storage method calls
        non_fields = {"vm"}
        missing = referenced_fields - declared_fields - non_fields
        for field in sorted(missing):
            # Infer type from usage patterns
            if re.search(rf"self\.{field}\.setter\([^)]+\)\.setter\(", rest_of_code):
                field_type = "mapping(uint256 => mapping(address => bool))"
            elif re.search(rf"self\.{field}\.setter\([^)]+\)\.set\(", rest_of_code):
                if re.search(rf"self\.{field}\.(?:get|setter)\([^)]*Address", rest_of_code):
                    field_type = "mapping(address => uint256)"
                else:
                    field_type = "mapping(uint256 => uint256)"
            elif re.search(rf"self\.{field}\.push\(", rest_of_code):
                field_type = "uint256[]"
            elif re.search(rf"self\.{field}\.get_string\(", rest_of_code):
                field_type = "string"
            else:
                field_type = "uint256"
            clean_lines.append(f"        {field_type} {field};")

        # Reconstruct the block
        pre_struct = block_content[: struct_brace + 1]
        post_struct = block_content[j:]
        new_struct_inner = "\n" + "\n".join(clean_lines) + "\n    "
        new_block = (
            "sol_storage! {"
            + pre_struct
            + new_struct_inner
            + post_struct
            + "\n}"
        )
        return code[:block_start] + new_block + code[block_end:]

    # ── Phase 1: Structural Validation ──

    def _structural_validate(self, code: str, template: Optional["StylusTemplate"]) -> str:
        """Phase 1: Validate and fix structural elements.

        Fix 1: Remove empty sol_storage! blocks
        Fix 2: Ensure proper cfg_attr
        Fix 3: Ensure extern crate alloc
        Fix 7: Ensure exactly one sol_storage! block with #[entrypoint]
        Fix 8: Ensure #[entrypoint] inside sol_storage!
        Fix 52: Sanitize sol_storage! block (structural validation)
        """
        fixed = code

        # Fix 1: Remove empty sol_storage! blocks
        fixed = re.sub(r"sol_storage!\s*\{\s*\}", "", fixed)

        # Fix 2: Ensure proper cfg_attr — must use (not(any(test, feature = "export-abi")))
        if "#![cfg_attr(not(any(test" not in fixed:
            if template:
                template_start = template.lib_rs.split("extern crate alloc")[0]
                if not fixed.startswith("#![cfg_attr"):
                    fixed = template_start + fixed
                else:
                    fixed = re.sub(
                        r'#!\[cfg_attr\(not\(any\(feature\s*=\s*"export-abi",\s*test\)\),\s*no_std\)\]',
                        '#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]',
                        fixed,
                    )
                    fixed = re.sub(
                        r"#!\[cfg_attr\(not\(test\),\s*no_main\)\]",
                        '#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]',
                        fixed,
                    )

        # Fix 3: Ensure extern crate alloc if missing
        if "extern crate alloc" not in fixed:
            fixed = re.sub(
                r"^(#!\[cfg_attr.*\n)+",
                r"\g<0>#[macro_use]\nextern crate alloc;\n\n",
                fixed,
                flags=re.MULTILINE,
            )

        # Fix 7: Ensure there's exactly one sol_storage! block with #[entrypoint]
        sol_storage_count = len(re.findall(r"sol_storage!\s*\{", fixed))
        if sol_storage_count == 0 and template:
            return template.lib_rs

        # Fix 8: Ensure #[entrypoint] is inside sol_storage! if missing
        if "#[entrypoint]" not in fixed:
            fixed = re.sub(
                r"sol_storage!\s*\{\s*(\n?\s*pub struct)",
                r"sol_storage! {\n    #[entrypoint]\1",
                fixed,
            )

        # Fix 52: Sanitize sol_storage! block — structural validation.
        # Strips invalid default values (= 0), removes garbled lines,
        # validates field declarations match Solidity-in-Rust syntax.
        fixed = self._sanitize_sol_storage(fixed, template)

        return fixed

    # ── Phase 2: Import Normalization ──

    def _normalize_imports(self, code: str) -> str:
        """Phase 2: Normalize and fix import statements.

        Fix 5: Handle Vec imports - avoid duplicates
        Fix 6: Ensure use alloc::vec; is present
        Fix 9c: Remove incorrect stylus_sdk::storage imports
        Fix 9d + Fix 37: Ensure correct alloc::string imports
        Fix 10: Fix wrong transfer_eth import paths
        Fix 13: Remove deprecated evm/msg imports
        Fix 20: Remove std::time imports
        Fix 21: Remove incorrect Call import
        """
        fixed = code

        # Fix 5: Handle Vec imports - avoid duplicates
        if "use alloc::vec::Vec;" in fixed and "use alloc::{" in fixed and "vec::Vec" in fixed:
            fixed = re.sub(r"use alloc::vec::Vec;\n?", "", fixed)
        if "Vec<u8>" in fixed and "alloc::vec::Vec" not in fixed and "alloc::{" not in fixed:
            fixed = re.sub(r"(extern crate alloc;)", r"\1\n\nuse alloc::vec::Vec;", fixed)

        # Fix 6: Ensure use alloc::vec; is present (sol_storage! needs vec module)
        if "use alloc::vec;" not in fixed and "use alloc::{" not in fixed:
            fixed = re.sub(
                r"(extern crate alloc;\s*\n)",
                r"\1\nuse alloc::{vec, vec::Vec};\n",
                fixed,
            )
        elif (
            "use alloc::vec::Vec;" in fixed
            and "use alloc::vec;" not in fixed
            and "alloc::{" not in fixed
        ):
            fixed = fixed.replace("use alloc::vec::Vec;", "use alloc::{vec, vec::Vec};")

        # Fix 9c: Remove incorrect stylus_sdk::storage imports
        storage_types = (
            r"StorageString|StorageMap|StorageVec"
            r"|StorageU\d+|StorageBool|StorageAddress"
        )
        fixed = re.sub(
            rf"^use stylus_sdk::storage"
            rf"(?:::(?:{storage_types}))?;\s*$",
            "",
            fixed,
            flags=re.MULTILINE,
        )

        # Fix 9d + Fix 37 (N31): Ensure correct alloc::string imports,
        # no duplicates.  Remove ALL existing alloc::string imports
        # and add one combined line.
        needs_string = (
            "-> String" in fixed
            or ": String" in fixed
            or ".to_string()" in fixed
            or "String::new" in fixed
            or "String::from" in fixed
        )
        needs_to_string = ".to_string()" in fixed
        if needs_string or needs_to_string:
            # Remove all existing alloc::string imports
            fixed = re.sub(
                r"^use alloc::string::\{[^}]*\};\s*\n?",
                "",
                fixed,
                flags=re.MULTILINE,
            )
            fixed = re.sub(
                r"^use alloc::string::\w+;\s*\n?",
                "",
                fixed,
                flags=re.MULTILINE,
            )
            # Build combined import
            parts = []
            if needs_string:
                parts.append("String")
            if needs_to_string:
                parts.append("ToString")
            if parts:
                if len(parts) == 1:
                    import_line = f"use alloc::string::{parts[0]};"
                else:
                    import_line = (
                        f"use alloc::string::{{{', '.join(parts)}}};"
                    )
                fixed = re.sub(
                    r"(use alloc::\{vec, vec::Vec\};)",
                    rf"\1\n{import_line}",
                    fixed,
                )

        # Fix 10: Fix wrong transfer_eth import paths
        fixed = re.sub(
            r"use stylus_sdk::call::transfer_eth;",
            "use stylus_sdk::call::transfer::transfer_eth;",
            fixed,
        )

        def _fix_call_import(m):
            pre = m.group(1).replace("transfer_eth", "").strip(", ")
            post = m.group(2).strip(", ")
            rest = (pre + post).strip(", ")
            base = "use stylus_sdk::call::transfer::transfer_eth;\n"
            if rest:
                return base + f"use stylus_sdk::call::{{{rest}}};"
            return base

        fixed = re.sub(
            r"use stylus_sdk::call::"
            r"\{([^}]*)\btransfer_eth\b([^}]*)\};",
            _fix_call_import,
            fixed,
        )
        fixed = re.sub(
            r"self\.transfer_eth\(([^)]+)\)",
            r"transfer_eth(self.vm(), \1)",
            fixed,
        )
        fixed = re.sub(
            r"transfer_eth\(self,\s*",
            "transfer_eth(self.vm(), ",
            fixed,
        )

        # Fix 13: Remove deprecated stylus_sdk::evm and stylus_sdk::msg imports
        fixed = re.sub(r"^use stylus_sdk::evm.*;\s*$", "", fixed, flags=re.MULTILINE)
        fixed = re.sub(r"^use stylus_sdk::msg.*;\s*$", "", fixed, flags=re.MULTILINE)

        # Fix 20: std::time::SystemTime — not available in no_std WASM
        fixed = re.sub(
            r"^use std::time.*;\s*$", "", fixed, flags=re.MULTILINE
        )
        fixed = re.sub(
            r"std::time::SystemTime::now\(\)[^;]*",
            "self.vm().block_timestamp()",
            fixed,
        )

        # Fix 21: Remove incorrect `use stylus_sdk::call::Call;` import
        # Call is available from prelude::* — no separate import needed
        fixed = re.sub(
            r"^use stylus_sdk::call::Call;\s*$",
            "",
            fixed,
            flags=re.MULTILINE,
        )

        return fixed

    # ── Phase 3: Storage Accessor Normalization ──

    def _normalize_storage_accessors(self, code: str) -> str:
        """Phase 3: Fix storage accessor patterns.

        Fix 22: StorageVec .setter(i).set(v) → .setter(i).unwrap().set(v)
        Fix 27: .get/.getter(k1).setter(k2) → .setter(k1).setter(k2)
        Fix 45: .get(key).field.setter( → .setter(key).field.setter(
        Fix 46: .field.set(key, value) → .field.setter(key).set(value)
        Fix 47: Normalize .get(key).getter(...) chains
        Fix 50: .setter().set() on simple fields
        Fix 51: Spurious .get()/.get_string() on mapping reads
        Fix 53: .get_string().unwrap → .get_string()
        Fix 55: .setter(key).unwrap() on mapping fields
        """
        fixed = code

        # Fix 22: StorageVec .setter(i).set(v) → .setter(i).unwrap().set(v)
        # StorageVec::setter(usize) returns Option, needs unwrap.
        # Only for dynamic array fields (type[] in sol_storage!), NOT mappings.
        array_fields = set()
        for af_match in re.finditer(r"\b\w+\[\]\s+(\w+)\s*;", fixed):
            array_fields.add(af_match.group(1))
        for af in array_fields:
            fixed = re.sub(
                rf"\.{af}\s*\.setter\(((?:[^()]*|\([^()]*\))*)\)\s*\.set\(",
                rf".{af}.setter(\1).unwrap().set(",
                fixed,
            )

        # Fix 27: .get/.getter(k1).setter(k2) → .setter(k1).setter(k2)
        # Nested mapping writes: .get()/.getter() return immutable ref,
        # can't call .setter() on it. Must chain .setter() for writes.
        fixed = re.sub(
            r"\.get\(((?:[^()]*|\([^()]*\))*)\)\s*\.setter\(",
            r".setter(\1).setter(",
            fixed,
        )
        fixed = re.sub(
            r"\.getter\(((?:[^()]*|\([^()]*\))*)\)\s*\.setter\(",
            r".setter(\1).setter(",
            fixed,
        )

        # Fix 45: .get(key).field.setter( → .setter(key).field.setter(
        # Nested struct writes: .get(key) on mapping returns immutable
        # StorageGuard, can't call .setter() on struct fields through it.
        # e.g. self.roles.get(role).members.setter(account).set(true)
        #   → self.roles.setter(role).members.setter(account).set(true)
        fixed = re.sub(
            r"\.get\(((?:[^()]*|\([^()]*\))*)\)((?:\.\w+)+)\.setter\(",
            r".setter(\1)\2.setter(",
            fixed,
        )

        # Fix 46: .field.set(key, value) → .field.setter(key).set(value)
        # StorageMap has no .set(k,v) method — must use .setter(k).set(v).
        # Only matches two-arg .set() calls (single-arg is valid on StorageGuardMut).
        fixed = re.sub(
            r"(\.\w+)\.set\(\s*((?:[^,()]*|\([^()]*\))*)\s*,\s*((?:[^,()]*|\([^()]*\))*)\s*\)",
            r"\1.setter(\2).set(\3)",
            fixed,
        )

        # Fix 47: Normalize .get(key).getter(...) chains.
        # .get(key) returns a value, .getter() is not a valid method on it.
        # Step a: .get(key).getter() → .getter(key) — preserve key when empty
        fixed = re.sub(
            r"\.get\(((?:[^()]*|\([^()]*\))+)\)\s*\.getter\(\)",
            r".getter(\1)",
            fixed,
        )
        # Step b: .get(key1).getter(key2...) → .getter(key2...) — strip .get()
        fixed = re.sub(
            r"\.get\(((?:[^()]*|\([^()]*\))*)\)\s*\.getter\(",
            r".getter(",
            fixed,
        )

        # Fix 50: .setter().set() / .setter(val).set(val) on simple fields.
        # StorageUint/StorageAddress/StorageBool have .set(val) directly.
        # .setter(key) is ONLY for StorageMap. Detect simple fields from
        # sol_storage! and fix wrong patterns.
        simple_field_types = {
            "uint256", "uint128", "uint64", "uint32", "uint16", "uint8",
            "int256", "int128", "int64", "int32", "int16", "int8",
            "address", "bool", "bytes32",
        }
        simple_fields_50 = set(
            re.findall(
                r"(?:" + "|".join(simple_field_types) + r")\s+(\w+)\s*;",
                fixed,
            )
        )
        for sf in simple_fields_50:
            # self.field.setter().set(val) → self.field.set(val)
            fixed = re.sub(
                rf"self\.{re.escape(sf)}\.setter\(\)\.set\(",
                rf"self.{sf}.set(",
                fixed,
            )
            # self.field.setter(val).set(val) → self.field.set(val)
            # (LLM passes the value to setter as if it were a key)
            fixed = re.sub(
                rf"self\.{re.escape(sf)}\.setter\(([^)]+)\)\.set\(\1\)",
                rf"self.{sf}.set(\1)",
                fixed,
            )

        # Fix 51: Spurious .get() / .get_string() on mapping reads.
        # (a) .get(key).get() → .get(key)
        #     Mapping .get(key) already returns the value directly,
        #     an extra parameterless .get() is always wrong.
        fixed = re.sub(
            r"\.get\(((?:[^()]*|\([^()]*\))*)\)\.get\(\)",
            r".get(\1)",
            fixed,
        )
        # (b) .get_string().get() → .get_string()
        #     get_string() returns String, extra .get() is wrong.
        fixed = re.sub(
            r"\.get_string\(\)\.get\(\)",
            ".get_string()",
            fixed,
        )
        # (c) .getter(key).get_string() on non-string mappings.
        #     Only mapping(... => string) uses .getter(k).get_string().
        #     For other mappings it should be .get(key).
        #     Detect string mappings, then fix non-string uses.
        string_map_fields = set(
            re.findall(r"mapping\([^)]*=>\s*string\)\s+(\w+)\s*;", fixed)
        )
        # Find all .getter(key).get_string() usages
        for m in re.finditer(
            r"self\.(\w+)\.getter\(([^)]+)\)\.get_string\(\)", fixed
        ):
            field = m.group(1)
            if field not in string_map_fields:
                # Not a string mapping — replace with .get(key)
                fixed = fixed.replace(
                    m.group(0),
                    f"self.{field}.get({m.group(2)})",
                )

        # Fix 53: .get_string().unwrap_or_default() → .get_string()
        # get_string() returns String (not Option), unwrap is wrong.
        fixed = re.sub(
            r"\.get_string\(\)\.unwrap_or_default\(\)",
            ".get_string()",
            fixed,
        )
        fixed = re.sub(
            r"\.get_string\(\)\.unwrap\(\)",
            ".get_string()",
            fixed,
        )

        # Fix 55: .setter(key).unwrap().set(val) → .setter(key).set(val)
        # StorageMap's .setter(key) returns StorageGuardMut directly,
        # NOT Option. Only StorageVec's .setter(idx) returns Option.
        # Detect mapping fields and strip spurious .unwrap() after .setter().
        map_fields_55 = set(
            re.findall(r"mapping\([^)]*\)\s+(\w+)\s*;", fixed)
        )
        for mf in map_fields_55:
            fixed = re.sub(
                rf"\.{re.escape(mf)}\.setter\(([^)]+)\)\.unwrap\(\)",
                rf".{mf}.setter(\1)",
                fixed,
            )

        return fixed

    # ── Phase 4: API Migration ──

    def _migrate_api(self, code: str) -> str:
        """Phase 4: Migrate deprecated API patterns to 0.10.0.

        Fix 9: sol! { interface } → sol_interface! { interface }
        Fix 9b: Storage* types → Solidity types in sol_storage!
        Fix 14: msg::sender()/msg::value() → self.vm()
        Fix 15: evm::log() → self.vm().log()
        Fix 17: self.vm().address() → self.vm().contract_address()
        Fix 18: U256::zero() → U256::ZERO
        Fix 29: sol_interface! snake_case method names
        Fix 32: sol_interface! host arg (self.vm() as first arg)
        """
        fixed = code

        # Fix 9: Convert sol! { interface } to sol_interface! { interface }
        fixed = re.sub(
            r"sol!\s*\{\s*(interface\b)",
            r"sol_interface! { \1",
            fixed,
        )

        # Fix 9b: Convert Rust Storage* types to Solidity types in sol_storage!
        # LLMs sometimes use Rust types instead of Solidity types
        fixed = fixed.replace("StorageString", "string")
        fixed = fixed.replace("StorageAddress", "address")
        fixed = fixed.replace("StorageU256", "uint256")
        fixed = fixed.replace("StorageU128", "uint128")
        fixed = fixed.replace("StorageU64", "uint64")
        fixed = fixed.replace("StorageU8", "uint8")
        fixed = fixed.replace("StorageBool", "bool")
        fixed = re.sub(
            r"StorageMap<Storage(\w+),\s*Storage(\w+)>",
            lambda m: f"mapping({m.group(1).lower()} => {m.group(2).lower()})",
            fixed,
        )
        fixed = re.sub(
            r"StorageVec<Storage(\w+)>",
            lambda m: f"{m.group(1).lower()}[]",
            fixed,
        )

        # Fix 14: Fix deprecated msg::sender()/msg::value() → self.vm()
        fixed = re.sub(r"msg::sender\(\)", "self.vm().msg_sender()", fixed)
        fixed = re.sub(r"msg::value\(\)", "self.vm().msg_value()", fixed)

        # Fix 15: Fix deprecated evm::log() → self.vm().log()
        fixed = re.sub(r"evm::log\(", "self.vm().log(", fixed)

        # Fix 17: self.vm().address() → self.vm().contract_address()
        fixed = fixed.replace(
            "self.vm().address()", "self.vm().contract_address()"
        )

        # Fix 18: U256::zero() / U128::zero() → U256::ZERO / U128::ZERO
        fixed = re.sub(r"U256::zero\(\)", "U256::ZERO", fixed)
        fixed = re.sub(r"U128::zero\(\)", "U128::ZERO", fixed)
        fixed = re.sub(r"U64::zero\(\)", "U64::ZERO", fixed)

        # Fix 29: sol_interface! generates snake_case Rust methods from
        # Solidity camelCase function names. Common wrong patterns:
        # Only apply when followed by (self.vm(), which signals sol_interface! call.
        sol_iface_renames = {
            "transferFrom": "transfer_from",
            "balanceOf": "balance_of",
            "ownerOf": "owner_of",
            "getApproved": "get_approved",
            "isApprovedForAll": "is_approved_for_all",
            "safeTransferFrom": "safe_transfer_from",
            "setApprovalForAll": "set_approval_for_all",
            "totalSupply": "total_supply",
            "latestAnswer": "latest_answer",
            "latestRoundData": "latest_round_data",
            "getRoundData": "get_round_data",
        }
        for camel, snake in sol_iface_renames.items():
            fixed = re.sub(
                rf"\.{camel}\(self\.vm\(\)",
                rf".{snake}(self.vm()",
                fixed,
            )

        # Fix 32: sol_interface! calls must have self.vm() as first
        # host argument.  LLMs often omit self.vm() and pass the
        # Call context as the first argument.
        # Pattern A: Call::new() as first argument
        fixed = re.sub(
            r"\b(\w+)\.(\w+)\(Call::new\(\)",
            r"\1.\2(self.vm(), Call::new()",
            fixed,
        )
        # Pattern B: Call::new_mutating(self) as first argument
        fixed = re.sub(
            r"\b(\w+)\.(\w+)\(Call::new_mutating\(self\)",
            r"\1.\2(self.vm(), Call::new_mutating(self)",
            fixed,
        )
        # Pattern C: Named Call variable as first argument
        call_var_matches = re.findall(
            r"let\s+(?:mut\s+)?(\w+)\s*=\s*Call::new", fixed
        )
        for cvar in call_var_matches:
            fixed = re.sub(
                rf"\b(\w+)\.(\w+)\({cvar},\s*",
                rf"\1.\2(self.vm(), {cvar}, ",
                fixed,
            )

        return fixed

    # ── Phase 5: Type Corrections ──

    def _correct_types(self, code: str) -> str:
        """Phase 5: Fix type-related errors.

        Fix 24: .unwrap_or_else(VALUE) → .unwrap_or(VALUE)
        Fix 25: self.vm().log(...)? → self.vm().log(...)
        Fix 26: .as_usize() → .to::<usize>()
        Fix 31: const U256::from(N) → U256::from_limbs([N, 0, 0, 0])
        Fix 48: B32 → B256
        Fix 56: I256::from(N_i128) → I256::from(N)
        """
        fixed = code

        # Fix 24: .unwrap_or_else(VALUE) → .unwrap_or(VALUE)
        # unwrap_or_else takes a closure, not a value. Fix for known constants.
        fixed = re.sub(
            r"\.unwrap_or_else\((\w+::(?:ZERO|MAX|MIN|ONE))\)",
            r".unwrap_or(\1)",
            fixed,
        )

        # Fix 25: self.vm().log(...)? → self.vm().log(...)
        # vm().log() returns (), not Result — cannot use ? operator
        fixed = re.sub(
            r"(self\.vm\(\)\.log\([^;]*\))\?",
            r"\1",
            fixed,
        )

        # Fix 26: .as_usize() → .to::<usize>()
        # U256 does not have as_usize(). Use Uint::to() method instead.
        fixed = re.sub(
            r"\.as_usize\(\)",
            ".to::<usize>()",
            fixed,
        )

        # N57: .as_u64() → .to::<u64>(), .as_u32() → .to::<u32>(), .as_u128() → .to::<u128>()
        # alloy-primitives 1.x Uint does not have .as_T() methods. Use .to::<T>().
        fixed = re.sub(r"\.as_u64\(\)", ".to::<u64>()", fixed)
        fixed = re.sub(r"\.as_u32\(\)", ".to::<u32>()", fixed)
        fixed = re.sub(r"\.as_u128\(\)", ".to::<u128>()", fixed)

        # Fix 31 (restored): const U256::from(N) → U256::from_limbs([N, 0, 0, 0])
        # From::from() is not a const fn. Cargo check catches E0015 but
        # the fix loop often generates wrong alternatives. Direct regex is safer.
        fixed = re.sub(
            r"const\s+(\w+)\s*:\s*U256\s*=\s*U256::from\((\d+)\)\s*;",
            r"const \1: U256 = U256::from_limbs([\2, 0, 0, 0]);",
            fixed,
        )

        # Fix 48: B32 → B256 for bytes32
        # LLM sometimes generates B32 (non-existent) instead of B256.
        # bytes32 maps to FixedBytes<32> which is aliased as B256.
        fixed = re.sub(r"\bB32\b", "B256", fixed)

        # Fix 56: I256::from(N_i128) → I256::from(N)
        # alloy-primitives 1.0.1 I256 (Signed<256,4>) implements From<i64>
        # but NOT From<i128>. Strip type suffix so Rust infers i64.
        fixed = re.sub(
            r"I256::from\((-?\d+)_i128\)",
            r"I256::from(\1)",
            fixed,
        )
        # Normalize any typed suffix on I256 literals
        fixed = re.sub(
            r"I256::from\((-?\d+)_[iu]\d+\)",
            r"I256::from(\1)",
            fixed,
        )

        return fixed

    # ── Phase 6: Output Sanitization ──

    def _sanitize_output(self, code: str) -> str:
        """Phase 6: Clean up garbled output and structural issues.

        Fix 39: Garbled LLM output cleanup
        Fix 40: Remove Debug from SolidityError derives
        Fix 41: Rename underscore-prefixed fns that conflict
        Fix 44: Remove phantom variable self-assignments
        Fix 49: Remove duplicate function definitions
        """
        fixed = code

        # Fix 39 (N36): Clean up garbled LLM output —
        # natural language mid-code and repeated return type fragments.
        fixed = re.sub(
            r"^.*(?:<<\s*\?\?\?|Wait,\s+we\s+need|Correction:|should be:|"
            r"Let me (?:re)?write|I'll fix|Actually,|Hmm,|Oops).*$",
            "",
            fixed,
            flags=re.MULTILINE,
        )
        # Fix garbled function sigs: `-> U256) -> U256) -> U256)` → `-> U256`
        fixed = re.sub(
            r"(->\s*\w+(?:<[^>]*>)?)\s*\)\s*(?:->\s*\w+(?:<[^>]*>)?\s*\)\s*)+",
            r"\1",
            fixed,
        )
        # Clean up stray `<< ??? >?` fragments
        fixed = re.sub(r"\s*<+\s*\?\?\?\s*>+\s*\??\s*", "", fixed)
        # Remove excess blank lines
        fixed = re.sub(r"\n{3,}", "\n\n", fixed)

        # Fix 40: Remove Debug from derives containing SolidityError.
        # sol! generated types don't implement Debug, so
        # #[derive(SolidityError, Debug)] fails to compile.
        def _remove_debug_from_solidity_error(m):
            content = m.group(1)
            if "SolidityError" in content and "Debug" in content:
                parts = [
                    p.strip()
                    for p in content.split(",")
                    if p.strip() and p.strip() != "Debug"
                ]
                return f"#[derive({', '.join(parts)})]"
            return m.group(0)

        fixed = re.sub(
            r"#\[derive\(([^)]+)\)\]",
            _remove_debug_from_solidity_error,
            fixed,
        )

        # Fix 41: Rename underscore-prefixed methods that conflict with
        # public methods in #[public] impl.
        # The #[public] proc macro strips leading underscores for ABI
        # selectors, so fn _grant_role and fn grant_role produce the same
        # selector ("unreachable pattern" error).
        # Fix: rename _xxx → xxx_internal (both definition and call sites).
        public_fns = set(re.findall(r"\bfn\s+([a-z]\w+)\s*\(", fixed))
        underscore_fns = set(re.findall(r"\bfn\s+(_[a-z]\w+)\s*\(", fixed))
        for ufn in underscore_fns:
            base = ufn[1:]  # strip leading underscore
            if base in public_fns:
                fixed = re.sub(
                    rf"\b{re.escape(ufn)}\b", f"{base}_internal", fixed
                )

        # Fix 42: address[] array deref returns FixedBytes<20>, not Address.
        # *self.list.get(idx).unwrap() → Address::from(*self.list.get(idx).unwrap())
        addr_array_fields = re.findall(r"\baddress\[\]\s+(\w+)", fixed)
        for field in addr_array_fields:
            fixed = re.sub(
                rf"(?<!Address::from\()\*self\.{re.escape(field)}\.get\("
                rf"([^)]+)\)\.unwrap\(\)",
                rf"Address::from(*self.{field}.get(\1).unwrap())",
                fixed,
            )

        # Fix 43: Remove extra .setter() on string mapping writes.
        # .setter(key).setter().set_str(val) → .setter(key).set_str(val)
        # StorageGuardMut<StorageString> has no .setter() method.
        fixed = re.sub(
            r"\.setter\(([^)]+)\)\.setter\(\)\.set_str\(",
            r".setter(\1).set_str(",
            fixed,
        )

        # Fix 44: Remove phantom variable self-assignments (let x = x;).
        # LLM generates `let role = role;` in helpers where `role` is not
        # a parameter — always a compile error. Even if it IS a parameter,
        # it's a redundant shadow. Safe to remove.
        fixed = re.sub(
            r"^\s*let\s+(?:mut\s+)?([a-z_]\w*)\s*=\s*\1\s*;\s*$",
            "",
            fixed,
            flags=re.MULTILINE,
        )

        # Fix 49: Remove duplicate function definitions.
        # Rust doesn't support overloading — two `fn foo(...)` in the
        # same impl block is a compile error.  LLM sometimes re-defines
        # a helper (e.g. _check_role_admin) with different signatures.
        # Keep the LAST definition (LLM often refines on second attempt).
        fn_def_pattern = re.compile(
            r"(\n[ \t]*)(pub\s+)?fn\s+(\w+)\s*\(", re.MULTILINE
        )
        fn_positions = [
            (m.group(3), m.start()) for m in fn_def_pattern.finditer(fixed)
        ]
        seen_fns: dict[str, list[int]] = {}
        for fn_name, pos in fn_positions:
            seen_fns.setdefault(fn_name, []).append(pos)
        # Remove earlier duplicates (keep last)
        to_remove: list[tuple[int, int]] = []  # (start, end) spans
        for fn_name, positions in seen_fns.items():
            if len(positions) < 2:
                continue
            for dup_pos in positions[:-1]:  # all except last
                # Find the opening brace
                brace_start = fixed.find("{", dup_pos)
                if brace_start == -1:
                    continue
                # Count braces to find matching closing brace
                depth = 0
                i = brace_start
                while i < len(fixed):
                    if fixed[i] == "{":
                        depth += 1
                    elif fixed[i] == "}":
                        depth -= 1
                        if depth == 0:
                            break
                    i += 1
                if depth == 0:
                    # Find the start of the fn line (back to newline)
                    line_start = fixed.rfind("\n", 0, dup_pos)
                    if line_start == -1:
                        line_start = 0
                    to_remove.append((line_start, i + 1))
        # Remove spans in reverse order to preserve positions
        for start, end in sorted(to_remove, reverse=True):
            fixed = fixed[:start] + fixed[end:]

        # N58: camelCase shorthand in struct initializers → explicit field: snake_case
        # sol! event/error structs have camelCase fields (Solidity convention), but
        # Rust variables are snake_case. LLM uses shorthand `MyError { newCap }`
        # which fails because no local `newCap` exists — should be
        # `MyError { newCap: new_cap }`.
        def _fix_camel_shorthand(m):
            struct_name = m.group(1)
            fields = m.group(2)
            # Skip sol! type definitions (event/error/interface/function)
            if re.match(r"\s*(?:event|error|interface|function)\s", fields):
                return m.group(0)
            changed = False

            def _camel_to_snake_field(fm):
                nonlocal changed
                camel = fm.group(1)
                snake = re.sub(r"([A-Z])", r"_\1", camel).lower()
                changed = True
                return f"{camel}: {snake}"

            fixed_fields = re.sub(
                r"\b([a-z][a-zA-Z]*[A-Z]\w*)\s*(?=[,}\n])",
                _camel_to_snake_field,
                fields,
            )
            if changed:
                return f"{struct_name} {{ {fixed_fields.strip()} }}"
            return m.group(0)

        fixed = re.sub(
            r"\b([A-Z]\w*)\s*\{([^}]*)\}",
            _fix_camel_shorthand,
            fixed,
        )

        return fixed

    # ── _fix_code Orchestrator ──

    def _fix_code(
        self, code: str, template: Optional["StylusTemplate"], target_version: str = "0.10.0"
    ) -> str:
        """Fix common LLM mistakes in generated code.

        Orchestrates 6 phases of fixes + version-specific fixes based on target_version.

        Args:
            code: Generated code to fix.
            template: Template used for generation (for fallback).
            target_version: Target SDK version (default "0.10.0").
        """
        is_010 = is_at_least_010(target_version)

        # ── GENERIC FIXES (all versions) ──
        # Phase 1: Structural validation (applies to all versions)
        fixed = self._structural_validate(code, template)

        # Fix 4: REMOVED — sol! is NOT in prelude, the explicit import is correct.
        # Previously this removed `use alloy_sol_types::sol;` which broke sol! events/errors.

        # ── VERSION-SPECIFIC FIXES ──

        if is_010:
            # 0.10.0 fixes — 6-phase architecture
            fixed = self._normalize_imports(fixed)
            fixed = self._normalize_storage_accessors(fixed)
            fixed = self._migrate_api(fixed)
            fixed = self._correct_types(fixed)
            fixed = self._sanitize_output(fixed)

            # Fix 16: MOVED TO CARGO CHECK — bare storage field reads
            # cargo check catches type mismatch when StorageType is used where
            # the value type is expected. Compiler fix loop handles it.

            # Fix 19: MOVED TO CARGO CHECK — StorageString API
            # cargo check catches E0599 (no method set/get on StorageString).
            # Compiler fix loop handles it with ERROR_GUIDANCE.

            # Fix 23: REMOVED — regex cannot distinguish sol! event/error
            # declarations from struct initialization. Applied inside sol! {}
            # blocks, it corrupts `event Foo(uint256 fieldName)` into
            # `event Foo(uint256 fieldName: field_name)` (invalid syntax).
            # System prompt rule 41 handles this via LLM guidance instead.

            # Fix 28: MOVED TO CARGO CHECK — .unwrap_or_default() on mapping reads
            # cargo check catches type mismatch (E0277). Compiler fix loop handles it.

            # Fix 30: MOVED TO CARGO CHECK — B256::from_uint()
            # cargo check catches missing method (E0599). Compiler fix loop handles it.

            # Fix 33: MOVED TO CARGO CHECK — B256::from_limbs()
            # cargo check catches missing method (E0599). Compiler fix loop handles it.

            # Fix 34: MOVED TO CARGO CHECK — string mapping reads
            # cargo check catches type mismatch (E0599/E0308). Compiler fix loop
            # handles it with ERROR_GUIDANCE for StorageString.

            # Fix 35: MOVED TO CARGO CHECK — .abi_encode() on enum wrapper
            # cargo check catches missing trait (E0599). Compiler fix loop handles it.

            # Fix 36: MOVED TO CARGO CHECK — StorageString bare access
            # cargo check catches type mismatch (E0308). Compiler fix loop handles it.

            # Fix 38: MOVED TO CARGO CHECK — pub const in #[public] impl
            # cargo check catches this with E0658. System prompt + compiler
            # verification handle the fix loop.
        else:
            # 0.9.x fixes (reverse direction)

            # Reverse: self.vm().msg_sender() → msg::sender()
            fixed = fixed.replace("self.vm().msg_sender()", "msg::sender()")
            fixed = fixed.replace("self.vm().msg_value()", "msg::value()")

            # Reverse: self.vm().log( → evm::log(
            fixed = fixed.replace("self.vm().log(", "evm::log(")

            # Reverse: sol_interface! { interface → sol! { interface
            fixed = re.sub(
                r"sol_interface!\s*\{\s*(interface\b)",
                r"sol! { \1",
                fixed,
            )

            # Reverse: transfer_eth import path
            fixed = fixed.replace(
                "use stylus_sdk::call::transfer::transfer_eth;",
                "use stylus_sdk::call::transfer_eth;",
            )

            # Reverse: .get( → .getter(
            fixed = re.sub(r"\.get\(", ".getter(", fixed)

            # Reverse: print_from_args() → print_abi()
            fixed = fixed.replace("print_from_args()", "print_abi()")

            # Add back evm/msg imports if needed
            if "msg::sender()" in fixed or "msg::value()" in fixed:
                if "use stylus_sdk::msg" not in fixed:
                    fixed = re.sub(
                        r"(use stylus_sdk::prelude::\*;)",
                        r"\1\nuse stylus_sdk::msg;",
                        fixed,
                    )
            if "evm::log(" in fixed:
                if "use stylus_sdk::evm" not in fixed:
                    fixed = re.sub(
                        r"(use stylus_sdk::prelude::\*;)",
                        r"\1\nuse stylus_sdk::evm;",
                        fixed,
                    )

        return fixed

    @staticmethod
    def _derive_project_name(prompt: str) -> str:
        """Derive a snake_case project name from the user prompt."""
        stop_words = {
            "a",
            "an",
            "the",
            "for",
            "with",
            "and",
            "or",
            "that",
            "this",
            "create",
            "build",
            "make",
            "generate",
            "implement",
        }
        words = [w.lower() for w in re.findall(r"[a-zA-Z]+", prompt) if w.lower() not in stop_words]
        name_words = words[:3] if words else ["stylus", "contract"]
        return "_".join(name_words)

    def _build_fix_prompt(self, code: str, error_text: str, guidance: str = "") -> str:
        """Build a prompt asking the LLM to fix compilation errors.

        Args:
            code: Current lib.rs code that failed to compile.
            error_text: Formatted error details from format_errors_for_llm().
            guidance: Stylus-specific fix guidance from format_fix_guidance().

        Returns:
            Prompt string for the LLM.
        """
        guidance_section = ""
        if guidance:
            guidance_section = f"""
STYLUS-SPECIFIC FIX GUIDANCE:
{guidance}
"""

        return f"""The following Stylus contract code has \
compilation errors. Fix ONLY the errors — do not \
change the contract's functionality or structure.

CURRENT CODE:
```rust
{code}
```

COMPILATION ERRORS:
{error_text}
{guidance_section}
Fix the code and return the complete, corrected lib.rs in a ```rust code block.
Keep the exact same structure and functionality. Only fix the compilation errors."""

    def _fix_cargo_toml(
        self, cargo: str, template: Optional["StylusTemplate"], target_version: str
    ) -> str:
        """Fix common LLM mistakes in generated Cargo.toml."""
        fixed = cargo

        # Ensure correct stylus-sdk version
        fixed = re.sub(r'stylus-sdk\s*=\s*"[^"]+"', f'stylus-sdk = "{target_version}"', fixed)

        # Ensure alloy-primitives uses exact version pin
        if 'alloy-primitives = "=' not in fixed:
            fixed = re.sub(
                r'alloy-primitives\s*=\s*"([^"=][^"]*)"', r'alloy-primitives = "=\1"', fixed
            )

        # Ensure alloy-sol-types uses exact version pin
        if 'alloy-sol-types = "=' not in fixed:
            fixed = re.sub(
                r'alloy-sol-types\s*=\s*"([^"=][^"]*)"', r'alloy-sol-types = "=\1"', fixed
            )

        # Ensure [profile.release] section exists
        if "[profile.release]" not in fixed:
            fixed += """

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s" """

        # Ensure [lib] section exists with cdylib
        if 'crate-type = ["lib", "cdylib"]' not in fixed:
            if "[lib]" not in fixed:
                fixed = re.sub(
                    r"\[features\]", '[lib]\ncrate-type = ["lib", "cdylib"]\n\n[features]', fixed
                )

        return fixed
