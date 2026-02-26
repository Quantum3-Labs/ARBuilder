"""
ask_stylus MCP Tool.

Answers questions, explains concepts, and helps debug Stylus code.
"""

import re
from typing import Optional

from .base import BaseTool
from .get_stylus_context import GetStylusContextTool

# Version manager — single source of truth for SDK versions
try:
    from src.utils.version_manager import (
        _to_major_minor,
        get_alloy_primitives_version,
        get_alloy_sol_types_version,
        get_main_version,
        get_version_patterns,
        is_at_least_010,
        load_version_config,
    )

    _HAS_VERSION_MANAGER = True
except ImportError:
    _HAS_VERSION_MANAGER = False

    def get_main_version():
        return "0.10.0"

    def get_version_patterns(v):
        return {}

    def get_alloy_primitives_version(v):
        return "1.0.1"

    def get_alloy_sol_types_version(v):
        return "1.0.1"

    def load_version_config():
        return {}

    def _to_major_minor(v):
        return ".".join(v.split(".")[:2])

    def is_at_least_010(v):
        return True


def get_system_prompt(target_version: str) -> str:
    """Generate a version-aware system prompt for ask_stylus.

    Reads SDK patterns and version info from version_manager config
    so the prompt never goes stale.
    """
    patterns = get_version_patterns(target_version)
    alloy_prim = get_alloy_primitives_version(target_version)
    alloy_sol = get_alloy_sol_types_version(target_version)

    sender = patterns.get("sender", "self.vm().msg_sender()")
    value = patterns.get("value", "self.vm().msg_value()")
    log = patterns.get("log", "self.vm().log(Event)")
    forbidden = patterns.get("forbidden_modules", [])
    required_files = patterns.get("required_files", [])
    abi_export = patterns.get("abi_export_fn", "print_from_args()")
    required_imports = patterns.get("required_imports", [])

    # Build breaking-changes section from config
    breaking_changes = ""
    try:
        config = load_version_config()
        ver_info = config.get("versions", {}).get(target_version, {})
        changes = ver_info.get("breaking_changes", [])
        if changes:
            breaking_changes = "\n".join(f"- {c}" for c in changes)
    except Exception:
        pass

    # Build forbidden-modules warning
    forbidden_section = ""
    if forbidden:
        forbidden_section = "\n".join(
            f"- Do NOT use `{m}` — removed in {target_version}" for m in forbidden
        )

    # Build required-files section
    required_files_section = ""
    if required_files:
        required_files_section = "\n".join(f"- {f}" for f in required_files)

    # Pre-compute optional sections
    imports_section = ""
    if required_imports:
        joined = ", ".join(f"`{i}`" for i in required_imports)
        imports_section = f"\nRequired imports: {joined}"
    forbidden_mod_section = ""
    if forbidden_section:
        forbidden_mod_section = f"\nForbidden modules:\n{forbidden_section}"
    req_files_section = ""
    if required_files_section:
        req_files_section = f"\nRequired project files:\n{required_files_section}"
    breaking_section = ""
    if breaking_changes:
        breaking_section = f"Breaking changes in {target_version}:\n{breaking_changes}"

    return f"""You are an expert Stylus smart contract \
developer and educator. You help developers understand \
and build Arbitrum Stylus contracts.

## CRITICAL VERSION INFORMATION
ALWAYS use these versions - ignore any outdated \
version info in retrieved context:
- stylus-sdk: {target_version} (current target)
- alloy-primitives: {alloy_prim}
- alloy-sol-types: {alloy_sol}

Standard Cargo.toml dependencies:
```toml
[dependencies]
stylus-sdk = "{target_version}"
alloy-primitives = "{alloy_prim}"
alloy-sol-types = "{alloy_sol}"
```

{breaking_section}

## KEY API PATTERNS for v{target_version}
- Get caller address: `{sender}`
- Get sent ETH value: `{value}`
- Emit events: `{log}`
- STORAGE ACCESS: ALWAYS use .get() to read: \
`self.field.get()` NOT `self.field`. \
ALWAYS use .set() to write.
- For mappings: `self.map.get(key)` \
and `self.map.setter(key).set(val)`
- Nested mapping writes: chain in one expression: \
`self.map.setter(k1).setter(k2).set(v)`
- TRANSFER ETH: \
`use stylus_sdk::call::transfer::transfer_eth;` \
then `transfer_eth(self.vm(), to, amount)?;`
- Error types: define with \
sol! {{ error MyError(...); }}, \
wrap enum with #[derive(SolidityError)]
- For .abi_encode() on errors: \
`use alloy_sol_types::SolError;`
- EXTERNAL INTERFACES: use `sol_interface!` \
(NOT `sol!`). Call pattern: \
`ifoo.method(self.vm(), Call::new(), arg1, arg2)?`
- ABI export function: `{abi_export}`
- Package name in Cargo.toml MUST use underscores
- crate-type = ["lib", "cdylib"]
{imports_section}\
{forbidden_mod_section}\
{req_files_section}

## REFERENCE CODE — use these EXACT patterns in your code examples

ETH transfer (withdraw/deposit/send ETH):
```rust
use stylus_sdk::call::transfer::transfer_eth;

pub fn withdraw(&mut self, to: Address, amount: U256) -> Result<(), Vec<u8>> {{
    transfer_eth(self.vm(), to, amount)?;
    Ok(())
}}
```

Cross-contract call (interact with another deployed contract):
```rust
sol_interface! {{
    interface IToken {{
        function balanceOf(address account) external view returns (uint256);
        function transfer(address to, uint256 amount) external returns (bool);
    }}
}}

// In a #[public] &mut self method:
pub fn get_balance(&mut self, token: Address, account: Address) -> Result<U256, Vec<u8>> {{
    let token_contract = IToken::new(token);
    let balance = token_contract.balance_of(self.vm(), Call::new(), account)?;
    Ok(balance)
}}
```

Storage access:
```rust
// Read: ALWAYS use .get()
let val = self.my_field.get();
let balance = self.balances.get(user);

// Write: use .set() or .setter().set()
self.my_field.set(new_val);
self.balances.setter(user).set(new_balance);
```

Your expertise includes:
- Stylus SDK and its features (sol_storage!, #[entrypoint], storage types)
- Rust programming patterns for smart contracts
- Arbitrum ecosystem and EVM compatibility
- Security best practices for smart contracts
- Debugging common issues in Stylus development
- Comparing Stylus with Solidity approaches

When answering:
1. Be clear and concise but thorough
2. Provide code examples when helpful
3. Cite relevant documentation or sources
4. Suggest follow-up topics when appropriate
5. For debugging, identify the specific issue and explain the fix
6. For concepts, explain at an appropriate level of detail
7. IMPORTANT: When asked about versions, ALWAYS use \
the version info above, NOT from retrieved context \
which may be outdated
"""


# Legacy constant for backwards compatibility
SYSTEM_PROMPT = get_system_prompt(get_main_version())

QUESTION_TYPE_PROMPTS = {
    "concept": "Explain this concept clearly with examples if helpful.",
    "debugging": "Identify the issue in the code, explain why it's a problem, and provide a fix.",
    "comparison": "Compare the approaches, highlighting key differences and trade-offs.",
    "howto": "Provide step-by-step instructions with code examples.",
    "general": "Answer the question thoroughly with relevant examples.",
}


class AskStylusTool(BaseTool):
    """
    Answers questions and helps with Stylus development.

    Provides concept explanations, debugging help, and guidance.
    """

    def __init__(
        self,
        context_tool: Optional[GetStylusContextTool] = None,
        **kwargs,
    ):
        """
        Initialize the tool.

        Args:
            context_tool: GetStylusContextTool for retrieving context.
        """
        super().__init__(**kwargs)
        self.context_tool = context_tool or GetStylusContextTool(**kwargs)

    def execute(
        self,
        question: str,
        code_context: Optional[str] = None,
        question_type: str = "general",
        target_version: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """
        Answer a question about Stylus development.

        Args:
            question: The question to answer.
            code_context: Optional code snippet for context (e.g., for debugging).
            question_type: Type of question (concept, debugging, comparison, howto, general).
            target_version: Target stylus-sdk version for version-specific guidance.

        Returns:
            Dict with answer, code_examples, references, follow_up_questions.
        """
        # Validate input
        if not question or not question.strip():
            return {"error": "Question is required and cannot be empty"}

        question = question.strip()

        # Check if question is Stylus-related
        stylus_keywords = [
            "stylus",
            "rust",
            "contract",
            "arbitrum",
            "storage",
            "entrypoint",
            "sol_storage",
            "erc",
            "token",
            "deploy",
            "wasm",
            "sdk",
        ]
        is_stylus_related = any(kw in question.lower() for kw in stylus_keywords)

        if not is_stylus_related and not code_context:
            return {
                "answer": (
                    "This question doesn't appear to be"
                    " related to Stylus or Arbitrum"
                    " development. I'm specialized in"
                    " helping with Stylus smart contract"
                    " development. Please ask about"
                    " Stylus concepts, code,"
                    " or debugging."
                ),
                "code_examples": [],
                "references": [],
                "follow_up_questions": [
                    "What is Stylus and how does it work?",
                    "How do I create my first Stylus contract?",
                    "What are the benefits of Stylus over Solidity?",
                ],
            }

        # Default to main version if not specified
        if not target_version:
            target_version = get_main_version()

        try:
            # Retrieve relevant context with version-aware scoring
            context_result = self.context_tool.execute(
                query=question,
                n_results=5,
                content_type="all",
                rerank=True,
                category_boosts=None,  # Use default Stylus-focused boosts
                target_version=target_version,
            )

            references = []
            context_text = ""

            if "contexts" in context_result:
                for ctx in context_result["contexts"]:
                    references.append(
                        {
                            "title": ctx["metadata"].get("title", "Reference"),
                            "source": ctx["source"],
                            "relevance": f"Relevance score: {ctx['relevance_score']:.2f}",
                        }
                    )
                    context_text += (
                        f"\n--- Reference: {ctx['source']} ---\n{ctx['content'][:1200]}\n"
                    )

            # Build prompt
            user_prompt = self._build_prompt(
                question=question,
                code_context=code_context,
                question_type=question_type,
                context_text=context_text,
            )

            # Generate answer with version-aware system prompt
            messages = [
                {"role": "system", "content": get_system_prompt(target_version)},
                {"role": "user", "content": user_prompt},
            ]

            response = self._call_llm(
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
            )

            # Parse response
            answer, code_examples = self._parse_response(response, target_version=target_version)

            # Generate follow-up questions
            follow_up_questions = self._generate_follow_ups(question, answer)

            return {
                "answer": answer,
                "code_examples": code_examples,
                "references": references[:5],  # Limit to 5 references
                "follow_up_questions": follow_up_questions,
            }

        except Exception as e:
            return {"error": f"Failed to answer question: {str(e)}"}

    def _build_prompt(
        self,
        question: str,
        code_context: Optional[str],
        question_type: str,
        context_text: str,
    ) -> str:
        """Build the question prompt."""
        parts = []

        # Add question type guidance
        type_guidance = QUESTION_TYPE_PROMPTS.get(question_type, QUESTION_TYPE_PROMPTS["general"])
        parts.append(f"Question type: {question_type}")
        parts.append(f"Guidance: {type_guidance}")
        parts.append("")

        # Add retrieved context
        if context_text:
            parts.append("Relevant documentation and examples for reference:")
            parts.append(context_text)
            parts.append("")

        # Add code context if debugging
        if code_context:
            parts.append("Code to analyze:")
            parts.append(f"```rust\n{code_context}\n```")
            parts.append("")

        # Add the question
        parts.append(f"Question: {question}")
        parts.append("")

        # Add response format guidance
        parts.append("Please provide:")
        parts.append("1. A clear, thorough answer")
        parts.append("2. Code examples if helpful (in ```rust code blocks)")
        parts.append("3. Any relevant caveats or best practices")

        return "\n".join(parts)

    def _fix_code_in_response(self, response: str, target_version: str = "0.10.0") -> str:
        """Fix common wrong patterns in code blocks within LLM responses.

        The RAG context often contains outdated SDK patterns that override
        the system prompt's correct patterns. This post-processes code blocks
        to fix the most critical compilation-breaking mistakes.

        For 0.10.0: fixes 0.9.x → 0.10.0 patterns (current behavior).
        For 0.9.x: fixes 0.10.0 → 0.9.x patterns (reverse).

        Args:
            response: Full LLM response text.
            target_version: Target SDK version.
        """
        is_010 = is_at_least_010(target_version)

        def fix_code_block(match: re.Match) -> str:
            lang = match.group(1) or ""
            code = match.group(2)

            # Only fix rust/toml code blocks (or unspecified)
            if lang and lang not in ("rust", "toml", ""):
                return match.group(0)

            if is_010:
                # ── 0.10.0 fixes (forward) ──

                code = re.sub(r"sol!\s*\{\s*(interface\b)", r"sol_interface! { \1", code)

                code = code.replace(
                    "use stylus_sdk::call::transfer_eth;",
                    "use stylus_sdk::call::transfer::transfer_eth;",
                )
                code = re.sub(
                    r"use stylus_sdk::call::\{([^}]*)\btransfer_eth\b([^}]*)\};",
                    lambda m: self._split_transfer_eth_import(m),
                    code,
                )
                code = re.sub(
                    r"self\.transfer_eth\(([^)]+)\)",
                    r"transfer_eth(self.vm(), \1)",
                    code,
                )
                code = re.sub(
                    r"transfer_eth\(self,\s*",
                    "transfer_eth(self.vm(), ",
                    code,
                )

                code = code.replace("msg::sender()", "self.vm().msg_sender()")
                code = code.replace("msg::value()", "self.vm().msg_value()")
                code = code.replace("evm::log(", "self.vm().log(")

                code = re.sub(r"^use stylus_sdk::evm.*;\s*$", "", code, flags=re.MULTILINE)
                code = re.sub(r"^use stylus_sdk::msg.*;\s*$", "", code, flags=re.MULTILINE)

                code = re.sub(r"\.getter\(", ".get(", code)

                # StorageMap/StorageVec/StorageX → Solidity types
                code = re.sub(
                    r"StorageMap<Storage(\w+),\s*Storage(\w+)>",
                    lambda m: f"mapping({m.group(1).lower()} => {m.group(2).lower()})",
                    code,
                )
                code = re.sub(
                    r"StorageVec<Storage(\w+)>",
                    lambda m: f"{m.group(1).lower()}[]",
                    code,
                )
                code = code.replace("StorageString", "string")
                code = code.replace("StorageAddress", "address")
                code = code.replace("StorageU256", "uint256")
                code = code.replace("StorageBool", "bool")
                code = code.replace("StorageU8", "uint8")
                code = code.replace("StorageU64", "uint64")
                code = code.replace("StorageU128", "uint128")

                # Fix self.vm().address() → self.vm().contract_address()
                code = code.replace(
                    "self.vm().address()",
                    "self.vm().contract_address()",
                )

                # Fix U256::zero() → U256::ZERO
                code = re.sub(r"U256::zero\(\)", "U256::ZERO", code)
                code = re.sub(r"U128::zero\(\)", "U128::ZERO", code)

                # Fix std::time in no_std
                code = re.sub(
                    r"^use std::time.*;\s*$", "", code, flags=re.MULTILINE
                )

                # Remove incorrect Call import
                code = re.sub(
                    r"^use stylus_sdk::call::Call;\s*$",
                    "",
                    code,
                    flags=re.MULTILINE,
                )

                # Fix StorageVec .setter(i).set() missing unwrap
                # Only on dynamic array fields (type[]), not mapping .setter()
                ask_array_fields = set()
                for af_m in re.finditer(
                    r"\b\w+\[\]\s+(\w+)\s*;", code
                ):
                    ask_array_fields.add(af_m.group(1))
                for af in ask_array_fields:
                    code = re.sub(
                        rf"\.{af}\.setter\(((?:[^()]*|\([^()]*\))*)\)\.set\(",
                        rf".{af}.setter(\1).unwrap().set(",
                        code,
                    )

                # Fix 27: .get(k1).setter(k2) → .setter(k1).setter(k2)
                code = re.sub(
                    r"\.get\(((?:[^()]*|\([^()]*\))*)\)\.setter\(",
                    r".setter(\1).setter(",
                    code,
                )

                # Fix 23: REMOVED — corrupts sol! event/error declarations.

                # Fix 28: Remove spurious .unwrap_or_default() on mapping reads
                mapping_flds = set()
                for mf_m in re.finditer(
                    r"mapping\(((?:[^()]*|\([^()]*\))*)\)\s+(\w+)\s*;",
                    code,
                ):
                    mapping_flds.add(mf_m.group(2))
                for mf in mapping_flds:
                    code = re.sub(
                        rf"\.{mf}\.get\(([^)]*)\)\.unwrap_or_default\(\)",
                        rf".{mf}.get(\1)",
                        code,
                    )
                    code = re.sub(
                        rf"\.{mf}\.getter\(([^)]*)\)\.get\(([^)]*)\)\.unwrap_or_default\(\)",
                        rf".{mf}.getter(\1).get(\2)",
                        code,
                    )

                # Fix 29: sol_interface! camelCase → snake_case
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
                    code = re.sub(
                        rf"\.{camel}\(self\.vm\(\)",
                        rf".{snake}(self.vm()",
                        code,
                    )

                # Fix 30: B256::from_uint(&expr) → B256::from(expr.to_be_bytes::<32>())
                code = re.sub(
                    r"B256::from_uint\(&(\w+)\)",
                    r"B256::from(\1.to_be_bytes::<32>())",
                    code,
                )

                # Fix 24: .unwrap_or_else(VALUE) → .unwrap_or(VALUE)
                code = re.sub(
                    r"\.unwrap_or_else\((\w+::(?:ZERO|MAX|MIN|ONE))\)",
                    r".unwrap_or(\1)",
                    code,
                )

                # Fix 25: self.vm().log(...)? → self.vm().log(...)
                code = re.sub(
                    r"(self\.vm\(\)\.log\([^;]*\))\?",
                    r"\1",
                    code,
                )

                # Fix 26: .as_usize() → .to::<usize>()
                code = re.sub(
                    r"\.as_usize\(\)",
                    ".to::<usize>()",
                    code,
                )
            else:
                # ── 0.9.x fixes (reverse) ──

                # sol_interface! → sol!
                code = re.sub(
                    r"sol_interface!\s*\{\s*(interface\b)",
                    r"sol! { \1",
                    code,
                )

                # transfer_eth import path
                code = code.replace(
                    "use stylus_sdk::call::transfer::transfer_eth;",
                    "use stylus_sdk::call::transfer_eth;",
                )

                # self.vm().msg_sender() → msg::sender()
                code = code.replace("self.vm().msg_sender()", "msg::sender()")
                code = code.replace("self.vm().msg_value()", "msg::value()")

                # self.vm().log( → evm::log(
                code = code.replace("self.vm().log(", "evm::log(")

                # .get( → .getter(
                code = re.sub(r"\.get\(", ".getter(", code)

                # print_from_args() → print_abi()
                code = code.replace("print_from_args()", "print_abi()")

                # Add evm/msg imports if needed
                if "msg::sender()" in code or "msg::value()" in code:
                    if "use stylus_sdk::msg" not in code:
                        code = re.sub(
                            r"(use stylus_sdk::prelude::\*;)",
                            r"\1\nuse stylus_sdk::msg;",
                            code,
                        )
                if "evm::log(" in code:
                    if "use stylus_sdk::evm" not in code:
                        code = re.sub(
                            r"(use stylus_sdk::prelude::\*;)",
                            r"\1\nuse stylus_sdk::evm;",
                            code,
                        )

            return f"```{lang}\n{code}```"

        # Fix all code blocks in the response
        return re.sub(r"```(\w*)\n([\s\S]*?)```", fix_code_block, response)

    def _split_transfer_eth_import(self, match: re.Match) -> str:
        """Split combined import that includes transfer_eth into separate imports."""
        before = match.group(1).replace("transfer_eth", "").strip().strip(",").strip()
        after = match.group(2).strip().strip(",").strip()
        others = ", ".join(filter(None, [before, after]))
        transfer_line = "use stylus_sdk::call::transfer::transfer_eth;"
        if others:
            return f"{transfer_line}\nuse stylus_sdk::call::{{{others}}};"
        return transfer_line

    def _parse_response(
        self, response: str, target_version: str = "0.10.0"
    ) -> tuple[str, list[dict]]:
        """Parse answer and code examples from response."""
        # Fix wrong patterns in code blocks before parsing
        response = self._fix_code_in_response(response, target_version=target_version)

        code_examples = []

        # Extract code blocks
        code_pattern = r"```(?:rust)?\s*([\s\S]*?)```"
        matches = re.findall(code_pattern, response)

        for i, match in enumerate(matches):
            code_examples.append(
                {
                    "description": f"Example {i + 1}",
                    "code": match.strip(),
                }
            )

        # Get the full answer text
        answer = response.strip()

        return answer, code_examples

    def _generate_follow_ups(self, question: str, answer: str) -> list[str]:
        """Generate relevant follow-up questions."""
        follow_ups = []

        # Check for topics mentioned in answer that could be expanded
        topic_follow_ups = {
            "sol_storage": "How do different storage types (StorageVec, StorageMap) work?",
            "entrypoint": "What happens when the entrypoint function is called?",
            "erc20": "How do I implement approve and transferFrom for ERC20?",
            "erc721": "How do I add metadata to my NFT tokens?",
            "storage": "What are the gas costs for different storage patterns?",
            "deploy": "How do I verify my Stylus contract after deployment?",
            "error": "How do I implement custom error types in Stylus?",
            "event": "How do I emit events from a Stylus contract?",
            "test": "How do I write unit tests for Stylus contracts?",
            "gas": "How can I optimize gas usage in my Stylus contract?",
            "security": "What are common security vulnerabilities in Stylus contracts?",
            "solidity": "How do Stylus and Solidity contracts interact?",
        }

        combined_text = (question + " " + answer).lower()

        for keyword, follow_up in topic_follow_ups.items():
            if keyword in combined_text and follow_up not in follow_ups:
                follow_ups.append(follow_up)
                if len(follow_ups) >= 3:
                    break

        # Add generic follow-ups if needed
        if len(follow_ups) < 2:
            generic = [
                "What are the best practices for this use case?",
                "Are there any security considerations I should know about?",
                "How would this be done differently in Solidity?",
            ]
            for g in generic:
                if g not in follow_ups:
                    follow_ups.append(g)
                    if len(follow_ups) >= 3:
                        break

        return follow_ups[:3]
