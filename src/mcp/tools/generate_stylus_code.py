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
4. STORAGE ACCESS: ALWAYS use .get() to read: \
`self.field.get()` NOT `self.field`. ALWAYS use \
.set() to write. For mappings: \
`self.map.get(key)` and \
`self.map.setter(key).set(val)`.
5. Use `{sender_pattern}` to get the caller address
6. Use `self.vm().msg_value()` for sent ETH value
7. Use `self.vm().log(Event {{ ... }})` to emit \
events (NOT evm::log)
8. Handle errors with {error_handling}
9. Include {cfg_attr}
10. Follow Rust naming conventions \
(snake_case for functions, PascalCase for types)
11. TRANSFER ETH: \
`use stylus_sdk::call::transfer::transfer_eth;` \
then `transfer_eth(self.vm(), to, amount)?;` \
— NOT self.transfer_eth() or call::transfer_eth()
12. For error types: define with \
sol! {{ error MyError(...); }}, \
wrap in enum with #[derive(SolidityError)]
13. For .abi_encode() on errors: import SolError \
via use alloy_sol_types::SolError;
14. Avoid chained .setter() borrows — get value \
with .get() first, then .setter().set() separately
15. Do NOT use `use stylus_sdk::evm` — removed \
in 0.10.0
16. Do NOT use `use stylus_sdk::msg` — use \
self.vm().msg_sender(), self.vm().msg_value()
17. ALWAYS include `use alloc::vec;` (the module) \
alongside `use alloc::vec::Vec;` — \
sol_storage! needs it
18. For ETH transfers via RawCall: \
`unsafe {{ let _ = \
RawCall::new_with_value(self.vm(), amount)\
.call(to, &[]); }}` — requires self.vm() as \
first arg and unsafe block
19. uint8 in sol_storage! maps to Uint<8,1> not \
native u8 — prefer uint256 unless specifically needed
20. Package name in Cargo.toml MUST use underscores \
(e.g., "my_contract") — hyphens prevent \
cargo-stylus from finding the WASM file
21. A src/main.rs is REQUIRED — cargo stylus deploy \
uses `cargo run` to check for constructors
22. The correct ABI export function in 0.10.0 is \
`print_from_args()` (NOT `print_abi()`)
23. crate-type in [lib] must be ["lib", "cdylib"] \
— "lib" is needed for bin target linking
24. EXTERNAL INTERFACES: use `sol_interface!` \
(NOT `sol!`) for external contract interfaces. \
CALL PATTERN: VIEW calls use \
`ifoo.method(self.vm(), Call::new(), args)?`. \
STATE-MODIFYING calls: extract Call first: \
`let call = Call::new_mutating(self);` then \
`ifoo.method(self.vm(), call, args)?`.
25. Stylus exports snake_case Rust fn names as \
camelCase in the ABI (create_market -> \
createMarket). Frontend must use camelCase \
in functionName.
26. Stylus &self view functions CANNOT make \
external contract calls (they revert). \
Use &mut self for cross-contract calls.
27. DYNAMIC ARRAYS: In sol_storage!, declare as \
`uint256[] items;` (Solidity syntax). \
Append primitives with `self.items.push(val)`. \
For struct arrays, use `self.items.grow()` then \
set fields on the returned accessor. \
Do NOT use `.setter(len).unwrap()` — it panics.
28. sol! MACRO IMPORT: When using sol! for events \
or errors, you MUST explicitly import it: \
`use alloy_sol_types::sol;` or combined \
`use alloy_sol_types::{{sol, SolError}};`. \
The sol! macro is NOT available from prelude::*.
29. BORROW CHECKER: Never combine .get() and \
.setter() on the same storage root in one expression. \
Extract values to local variables first: \
`let sender = self.vm().msg_sender(); \
self.balances.setter(sender).set(amount);`
30. sol! EVENT/ERROR FIELDS: Use camelCase for \
field names in sol! {{ }} blocks (Solidity convention). \
Example: `event Transfer(address indexed from, \
address indexed to, uint256 tokenId);` \
NOT snake_case like `token_id`.
31. Cross-contract CALL CONTEXTS: \
`Call::new()` for VIEW (read-only) calls. \
`Call::new_mutating(self)` for STATE-MODIFYING \
calls (transfer, approve, etc.). \
IMPORTANT: extract the Call to a local variable \
before using it: `let call = Call::new_mutating(self);` \
then `tok.transfer(self.vm(), call, to, amount)?;` \
— this avoids borrow checker conflicts.

Dependencies for v{target_version}:
- stylus-sdk = "{target_version}"
- alloy-primitives = "{alloy_version}"

Required project files (SDK 0.10.0+):
- Stylus.toml with [workspace], \
[workspace.networks], and [contract] sections
- rust-toolchain.toml with channel = "1.91.0"
- src/main.rs with print_from_args() for ABI export

When generating code:
- Generate complete, compilable Rust code
- Include all necessary imports incl. `use alloc::vec;`
- Add helpful comments for complex logic
- Use proper error handling
- Follow security best practices \
(check for overflows, validate inputs)
- Do NOT use deprecated msg::sender(), \
msg::value(), or evm::log() — use self.vm() methods
32. CONTRACT ADDRESS: Use `self.vm().contract_address()` \
to get this contract's address. Do NOT use \
`self.vm().address()` — it does not exist.
33. ZERO CONSTANTS: Use uppercase constants \
`U256::ZERO`, `Address::ZERO`, `U128::ZERO`. \
Do NOT use `U256::zero()` or `Address::zero()` \
— these functions do not exist.
34. BLOCK TIMESTAMP: `self.vm().block_timestamp()` \
returns `u64`. When storing in a `uint256` field, \
wrap with `U256::from(self.vm().block_timestamp())`.
35. StorageString: Use `.set_str("value")` to write \
and `.get_string()` to read. Do NOT use `.set()` or \
`.get()` on string storage fields — they don't exist.
36. NO STD LIBRARY: This is a `no_std` WASM environment. \
Do NOT use `std::time`, `std::collections`, `std::io`, \
or any other std library. For timestamps use \
`self.vm().block_timestamp()`.
37. EVENT/ERROR NAMING: Never give an event and error \
the same name. For example, do NOT define both \
`event Paused(address account)` and `error Paused()` \
— they generate conflicting Rust structs. Use distinct \
names like `event Paused(address)` and \
`error ContractPaused()`.
38. RESULT PROPAGATION: When calling helper methods \
that return `Result`, ALWAYS use `?` to propagate: \
`self._require_owner()?;` — NOT \
`self._require_owner();` which silently ignores errors.
39. Call IMPORT: `Call` is available from \
`stylus_sdk::prelude::*` — do NOT add \
`use stylus_sdk::call::Call;` separately.
40. DUPLICATE DEFINITIONS: Never define the same \
error or event name twice with different fields. \
Put all errors in a single `sol! {{ }}` block.
41. sol! STRUCT INITIALIZATION: When constructing \
sol! event/error structs, ALWAYS use explicit field \
assignment: `MyEvent {{ fieldName: my_var }}`. \
NEVER use Rust shorthand `MyEvent {{ fieldName }}` \
because sol! fields are camelCase but Rust variables \
are snake_case — shorthand WILL fail to compile. \
Example: `OwnershipTransferred {{ newOwner: new_owner }}` \
NOT `OwnershipTransferred {{ newOwner }}`.
42. StorageVec API: `StorageVec::len()` returns `usize` \
(NOT `U256`). Use `usize` for loop indices when \
iterating. `StorageVec::setter(index)` returns \
`Option<StorageGuardMut>` — MUST call `.unwrap()` \
before `.set()`. Example: \
`self.items.setter(i).unwrap().set(val);` \
For reading: `self.items.getter(i).unwrap()`. \
To convert U256 to usize: `index.to::<usize>()`. \
Do NOT use `.as_usize()` — it does not exist.
43. SolidityError ENUM: Each variant MUST wrap a \
DISTINCT error type. Never have two variants wrapping \
the same type: `NotOwner(NotOwner)` and \
`NotTokenOwner(NotOwner)` — `#[derive(SolidityError)]` \
generates conflicting `From<NotOwner>` impls. \
Fix: define `error NotTokenOwner(address caller)` \
as its own distinct error type.
44. U8 TYPE: `uint8` in sol_storage! maps to `U8` \
(alias for `Uint<8,1>`), NOT native `u8`. \
To set: `self.decimals.set(U8::from(18u8))`. \
To read as u8: `self.decimals.get().to::<u8>()` \
or `.try_into().unwrap_or(18u8)`. \
Import U8 from `stylus_sdk::alloy_primitives::U8`.
45. MUTABLE BINDINGS: When you store a `.setter()` \
result in a variable and then call methods on it, \
the binding must be `let mut`. Example: \
`let mut inner = self.allowances.setter(owner); \
inner.setter(spender).set(amount);`
46. vm().log() RETURN TYPE: `self.vm().log(event)` \
returns `()` (unit type), NOT `Result`. \
Do NOT use `?` after it. Just call it directly: \
`self.vm().log(MyEvent {{ field1: val }});`
47. unwrap_or vs unwrap_or_else: `unwrap_or(VALUE)` \
takes a direct value. `unwrap_or_else(|| VALUE)` \
takes a closure. Do NOT pass a value to \
unwrap_or_else — use unwrap_or instead. \
Example: `.unwrap_or(U256::ZERO)` NOT \
`.unwrap_or_else(U256::ZERO)`.
48. sol_storage! TYPES: Inside sol_storage! {{ }}, use \
SOLIDITY type syntax, NOT Rust Storage* types. \
Use: `uint256`, `address`, `bool`, `string`, \
`mapping(address => uint256)`, `uint256[]`. \
Do NOT use: `StorageU256`, `StorageAddress`, \
`StorageString`, `StorageMap<...>`, `StorageVec<...>`. \
These Rust wrapper types are internal to the SDK.
49. NESTED MAPPING WRITES: To write to nested \
mappings like `mapping(address => mapping(address \
=> uint256))`, chain `.setter()` calls: \
`self.allowances.setter(owner).setter(spender)\
.set(amount);` \
Do NOT use tuple keys: \
`self.allowances.setter((owner, spender))` — \
tuple indexing does NOT exist. \
Do NOT mix .get() and .setter() on the same root: \
`self.allowances.get(owner).setter(spender)` — \
.get() returns an immutable reference that \
conflicts with .setter()'s mutable borrow. \
ALWAYS chain .setter() for writes.
50. MAPPING READS RETURN VALUES DIRECTLY: \
`StorageMap::get(key)` returns the value type \
directly (zero-default for uninitialized), NOT \
`Option`. Do NOT call `.unwrap_or_default()` on \
mapping reads. Both single and nested mappings: \
`self.balances.get(user)` returns `U256`, \
`self.allowances.getter(owner).get(spender)` \
returns `U256`. Just use the returned value directly.
51. sol_interface! GENERATES SNAKE_CASE METHODS: \
The `sol_interface!` macro converts Solidity \
camelCase function names to Rust snake_case. \
`function transferFrom(...)` becomes \
`.transfer_from(...)`. `function balanceOf(...)` \
becomes `.balance_of(...)`. \
ALWAYS use snake_case when calling sol_interface! \
methods in Rust code.
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
8. KEEP the Cargo.toml [profile.release] section \
exactly as provided

COMPILATION-CRITICAL — these WILL break the build:
- STORAGE ACCESS: ALWAYS use .get() to read storage: \
`self.field.get()` NOT `self.field`. ALWAYS use \
.set(val) to write: `self.field.set(val)`. \
For mappings: read with `self.map.get(key)`, \
write with `self.map.setter(key).set(val)`.
- TRANSFER ETH: \
`use stylus_sdk::call::transfer::transfer_eth;` \
then `transfer_eth(self.vm(), to, amount)?;`. \
Do NOT use `self.transfer_eth()`, \
`call::transfer_eth()`, or any other path.
- EXTERNAL INTERFACES: use `sol_interface!` macro \
(NOT `sol!`). `sol!` is ONLY for events and errors.
- CROSS-CONTRACT CALLS: VIEW calls: \
`ifoo.method(self.vm(), Call::new(), args)?`. \
STATE-MODIFYING calls: extract Call first: \
`let call = Call::new_mutating(self);` then \
`ifoo.method(self.vm(), call, args)?` — this \
avoids borrow checker conflicts.
- External calls require `&mut self` \
(NOT `&self` — view functions revert)
- DYNAMIC ARRAYS: In sol_storage!, declare as \
`uint256[] items;`. Append with \
`self.items.push(val)` for primitives, \
`self.items.grow()` for structs. \
Do NOT use `.setter(len).unwrap()`.
- BORROW CHECKER: Extract values to local vars \
before combining storage reads and writes: \
`let sender = self.vm().msg_sender(); \
self.balances.setter(sender).set(amount);`
- sol! EVENT/ERROR FIELDS: Use camelCase \
(Solidity convention): `tokenId` NOT `token_id`.
- CONTRACT ADDRESS: `self.vm().contract_address()` \
NOT `self.vm().address()` (does not exist).
- ZERO CONSTANTS: `U256::ZERO`, `Address::ZERO` \
(uppercase const). NOT `U256::zero()` (does not exist).
- BLOCK TIMESTAMP: `self.vm().block_timestamp()` \
returns `u64`. Wrap with `U256::from()` before storing \
in uint256 fields.
- StorageString: `.set_str("val")` and `.get_string()`. \
NOT `.set()` or `.get()`.
- NO STD: Do NOT use `std::time`, `std::collections`. \
For timestamps: `self.vm().block_timestamp()`.
- EVENT/ERROR NAMING: Never give an event and error \
the same name — they generate conflicting Rust structs. \
Use `event Paused(address)` and `error ContractPaused()`.
- RESULT PROPAGATION: Always use `?` to propagate \
`Result` from helper methods. `self.check()?;` not \
`self.check();`
- Call IMPORT: `Call` comes from `prelude::*`. \
Do NOT add `use stylus_sdk::call::Call;` separately.
- DUPLICATE DEFINITIONS: Put all errors in one \
`sol! {{ }}` block. Never define the same name twice.
- sol! STRUCT INIT: When constructing sol! event/error \
structs, ALWAYS use explicit field assignment: \
`MyEvent {{ fieldName: my_var }}`. NEVER use Rust \
shorthand `MyEvent {{ fieldName }}` — sol! fields are \
camelCase but Rust variables are snake_case.
- StorageVec API: `len()` returns `usize` (NOT U256). \
Use `usize` for loop indices. `setter(i)` returns \
`Option` — call `.unwrap()` before `.set()`. \
`getter(i)` also returns `Option` — call `.unwrap()`. \
To convert U256 to usize: `index.to::<usize>()`.
- SolidityError ENUM: Each variant must wrap a DISTINCT \
error type. Two variants wrapping the same type cause \
conflicting `From` impls.
- U8 TYPE: `uint8` → `U8` (Uint<8,1>), not native u8. \
Set: `U8::from(18u8)`. Read: `.to::<u8>()`.
- MUTABLE BINDINGS: `.setter()` result stored in a \
variable needs `let mut` if methods are called on it.
- vm().log() returns `()` — do NOT use `?` after it.
- unwrap_or vs unwrap_or_else: `.unwrap_or(VALUE)` \
for values, `.unwrap_or_else(|| VALUE)` for closures.
- sol_storage! TYPES: Use SOLIDITY syntax inside \
sol_storage!: `uint256`, `address`, `bool`, `string`, \
`mapping(...)`, `type[]`. NOT Rust Storage* types \
like `StorageU256`, `StorageString`, etc.
- NESTED MAPPING WRITES: Chain `.setter()` calls: \
`self.map.setter(k1).setter(k2).set(v);` \
Do NOT use tuple keys `(k1, k2)`. \
Do NOT mix `.get()` then `.setter()` — \
`.get()` returns immutable ref conflicting with \
`.setter()`'s mutable borrow.
- MAPPING READS: `StorageMap::get(key)` returns \
the value directly (zero-default), NOT `Option`. \
Do NOT call `.unwrap_or_default()` on mapping reads. \
Nested: `.getter(k1).get(k2)` returns value directly.
- sol_interface! SNAKE_CASE: `sol_interface!` \
converts Solidity camelCase to Rust snake_case. \
`transferFrom` → `.transfer_from()`, \
`balanceOf` → `.balance_of()`.

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

ETH transfer (withdraw/deposit/send ETH):
```rust
use stylus_sdk::call::transfer::transfer_eth;

pub fn withdraw(&mut self, to: Address, amount: U256) -> Result<(), Vec<u8>> {{
    transfer_eth(self.vm(), to, amount)?;
    Ok(())
}}
```

Cross-contract VIEW call (read-only — Call::new() is fine):
```rust
sol_interface! {{
    interface IPriceFeed {{
        function latestPrice() external view returns (uint256);
    }}
}}

pub fn get_price(&mut self, feed_addr: Address) -> Result<U256, Vec<u8>> {{
    let feed = IPriceFeed::new(feed_addr);
    let price = feed.latest_price(self.vm(), Call::new())?;
    Ok(price)
}}
```

Cross-contract state-modifying call (extract Call to avoid borrow conflict):
```rust
sol_interface! {{
    interface IToken {{
        function transfer(address to, uint256 amount) external returns (bool);
    }}
}}

pub fn transfer_tokens(
    &mut self, token: Address, to: Address, amount: U256,
) -> Result<bool, Vec<u8>> {{
    let tok = IToken::new(token);
    let call = Call::new_mutating(self);
    let success = tok.transfer(self.vm(), call, to, amount)?;
    Ok(success)
}}
```

Dynamic array (append to sol_storage! array):
```rust
// In sol_storage!: uint256[] items;
// Append primitive:
self.items.push(new_val);
// For structs: let mut entry = self.items.grow(); entry.field.set(val);
```

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

    MAX_COMPILE_ATTEMPTS = 2

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
                    fix_prompt = self._build_fix_prompt(code, error_text)

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

    def _fix_code(
        self, code: str, template: Optional["StylusTemplate"], target_version: str = "0.10.0"
    ) -> str:
        """Fix common LLM mistakes in generated code.

        Applies generic fixes (all versions) + version-specific fixes based on target_version.

        Args:
            code: Generated code to fix.
            template: Template used for generation (for fallback).
            target_version: Target SDK version (default "0.10.0").
        """
        fixed = code
        is_010 = is_at_least_010(target_version)

        # ── GENERIC FIXES (all versions) ──

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

        # Fix 4: REMOVED — sol! is NOT in prelude, the explicit import is correct.
        # Previously this removed `use alloy_sol_types::sol;` which broke sol! events/errors.

        # Fix 5: Handle Vec imports - avoid duplicates
        if "use alloc::vec::Vec;" in fixed and "use alloc::{" in fixed and "vec::Vec" in fixed:
            fixed = re.sub(r"use alloc::vec::Vec;\n?", "", fixed)
        if "Vec<u8>" in fixed and "alloc::vec::Vec" not in fixed and "alloc::{" not in fixed:
            fixed = re.sub(r"(extern crate alloc;)", r"\1\n\nuse alloc::vec::Vec;", fixed)

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

        # ── VERSION-SPECIFIC FIXES ──

        if is_010:
            # 0.10.0 fixes (current behavior)

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

            # Fix 9d: Add `use alloc::string::String;` if String is used but not imported
            if "-> String" in fixed or ": String" in fixed:
                if "alloc::string::String" not in fixed and "alloc::string::" not in fixed:
                    fixed = re.sub(
                        r"(use alloc::\{vec, vec::Vec\};)",
                        r"\1\nuse alloc::string::String;",
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

            # Fix 14: Fix deprecated msg::sender()/msg::value() → self.vm()
            fixed = re.sub(r"msg::sender\(\)", "self.vm().msg_sender()", fixed)
            fixed = re.sub(r"msg::value\(\)", "self.vm().msg_value()", fixed)

            # Fix 15: Fix deprecated evm::log() → self.vm().log()
            fixed = re.sub(r"evm::log\(", "self.vm().log(", fixed)

            # Fix 16: Enforce .get() on bare storage field reads
            storage_fields = set()
            for field_match in re.finditer(
                r"\b(?:uint\d*|int\d*|address|bool|string|bytes\d*)\s+(\w+)\s*;",
                fixed,
            ):
                storage_fields.add(field_match.group(1))
            for field_match in re.finditer(
                r"mapping\(((?:[^()]*|\([^()]*\))*)\)\s+(\w+)\s*;",
                fixed,
            ):
                storage_fields.add(field_match.group(2))
            for field in storage_fields:
                fixed = re.sub(
                    rf"(\w+)\.{field}\b(?!\s*[.(])",
                    rf"\1.{field}.get()",
                    fixed,
                )

            # Fix 17: self.vm().address() → self.vm().contract_address()
            fixed = fixed.replace(
                "self.vm().address()", "self.vm().contract_address()"
            )

            # Fix 18: U256::zero() / U128::zero() → U256::ZERO / U128::ZERO
            fixed = re.sub(r"U256::zero\(\)", "U256::ZERO", fixed)
            fixed = re.sub(r"U128::zero\(\)", "U128::ZERO", fixed)
            fixed = re.sub(r"U64::zero\(\)", "U64::ZERO", fixed)

            # Fix 19: StorageString - .set() → .set_str(), .get() → .get_string()
            string_fields = set()
            for sf_match in re.finditer(
                r"\bstring\s+(\w+)\s*;", fixed
            ):
                string_fields.add(sf_match.group(1))
            for sf in string_fields:
                fixed = re.sub(
                    rf"\.{sf}\.set\(", f".{sf}.set_str(", fixed
                )
                fixed = re.sub(
                    rf"\.{sf}\.get\(\)", f".{sf}.get_string()", fixed
                )

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

            # Fix 22: StorageVec .setter(i).set(v) → .setter(i).unwrap().set(v)
            # StorageVec::setter(usize) returns Option, needs unwrap.
            # BUT mapping .setter(key) does NOT return Option — no unwrap needed.
            # Strategy: detect dynamic array fields from sol_storage! (type[])
            # and only add .unwrap() on those fields.
            array_fields = set()
            for af_match in re.finditer(
                r"\b\w+\[\]\s+(\w+)\s*;", fixed
            ):
                array_fields.add(af_match.group(1))
            for af in array_fields:
                # .field.setter(x).set( → .field.setter(x).unwrap().set(
                # Use balanced-paren pattern to handle nested parens
                # e.g. setter(U256::from(idx as u64))
                fixed = re.sub(
                    rf"\.{af}\.setter\(((?:[^()]*|\([^()]*\))*)\)\.set\(",
                    rf".{af}.setter(\1).unwrap().set(",
                    fixed,
                )

            # Fix 27: .get(k1).setter(k2) → .setter(k1).setter(k2)
            # Nested mapping writes: .get() returns immutable ref, can't
            # call .setter() on it. Must chain .setter() for writes.
            fixed = re.sub(
                r"\.get\(((?:[^()]*|\([^()]*\))*)\)\.setter\(",
                r".setter(\1).setter(",
                fixed,
            )

            # Fix 23: REMOVED — regex cannot distinguish sol! event/error
            # declarations from struct initialization. Applied inside sol! {}
            # blocks, it corrupts `event Foo(uint256 fieldName)` into
            # `event Foo(uint256 fieldName: field_name)` (invalid syntax).
            # System prompt rule 41 handles this via LLM guidance instead.

            # Fix 28: Remove spurious .unwrap_or_default() on mapping reads.
            # StorageMap::get() returns the value directly (zero-default for
            # uninitialized), NOT Option. .unwrap_or_default() won't compile.
            # Applies to both direct and nested mapping reads.
            # e.g. self.map.get(key).unwrap_or_default() → self.map.get(key)
            # e.g. self.map.getter(k1).get(k2).unwrap_or_default() → .getter(k1).get(k2)
            # Use balanced-paren regex for nested mapping declarations like
            # mapping(address => mapping(address => uint256)) allowances;
            mapping_fields = set()
            for mf_match in re.finditer(
                r"mapping\(((?:[^()]*|\([^()]*\))*)\)\s+(\w+)\s*;", fixed
            ):
                mapping_fields.add(mf_match.group(2))
            for mf in mapping_fields:
                # Direct: .field.get(key).unwrap_or_default()
                fixed = re.sub(
                    rf"\.{mf}\.get\(([^)]*)\)\.unwrap_or_default\(\)",
                    rf".{mf}.get(\1)",
                    fixed,
                )
                # Nested via .getter(): .field.getter(k1).get(k2).unwrap_or_default()
                fixed = re.sub(
                    rf"\.{mf}\.getter\(([^)]*)\)\.get\(([^)]*)\)\.unwrap_or_default\(\)",
                    rf".{mf}.getter(\1).get(\2)",
                    fixed,
                )

            # Fix 29: sol_interface! generates snake_case Rust methods from
            # Solidity camelCase function names. Common wrong patterns:
            # .transferFrom(  → .transfer_from(
            # .balanceOf(     → .balance_of(
            # .allowance is already lowercase — no change needed
            # .ownerOf(       → .owner_of(
            # .getApproved(   → .get_approved(
            # .isApprovedForAll( → .is_approved_for_all(
            # .safeTransferFrom( → .safe_transfer_from(
            # .setApprovalForAll( → .set_approval_for_all(
            # .totalSupply(   → .total_supply(
            # .latestAnswer(  → .latest_answer(
            # .latestRoundData( → .latest_round_data(
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

    def _build_fix_prompt(self, code: str, error_text: str) -> str:
        """Build a prompt asking the LLM to fix compilation errors.

        Args:
            code: Current lib.rs code that failed to compile.
            error_text: Formatted error details from format_errors_for_llm().

        Returns:
            Prompt string for the LLM.
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
