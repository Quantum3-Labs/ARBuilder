"""
ask_stylus MCP Tool.

Answers questions, explains concepts, and helps debug Stylus code.
"""

import re
from typing import Optional

from .base import BaseTool
from .get_stylus_context import GetStylusContextTool


SYSTEM_PROMPT = """You are an expert Stylus smart contract developer and educator. You help developers understand and build Arbitrum Stylus contracts.

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
"""

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
        **kwargs,
    ) -> dict:
        """
        Answer a question about Stylus development.

        Args:
            question: The question to answer.
            code_context: Optional code snippet for context (e.g., for debugging).
            question_type: Type of question (concept, debugging, comparison, howto, general).

        Returns:
            Dict with answer, code_examples, references, follow_up_questions.
        """
        # Validate input
        if not question or not question.strip():
            return {"error": "Question is required and cannot be empty"}

        question = question.strip()

        # Check if question is Stylus-related
        stylus_keywords = [
            "stylus", "rust", "contract", "arbitrum", "storage", "entrypoint",
            "sol_storage", "erc", "token", "deploy", "wasm", "sdk"
        ]
        is_stylus_related = any(kw in question.lower() for kw in stylus_keywords)

        if not is_stylus_related and not code_context:
            return {
                "answer": "This question doesn't appear to be related to Stylus or Arbitrum development. I'm specialized in helping with Stylus smart contract development. Please ask about Stylus concepts, code, or debugging.",
                "code_examples": [],
                "references": [],
                "follow_up_questions": [
                    "What is Stylus and how does it work?",
                    "How do I create my first Stylus contract?",
                    "What are the benefits of Stylus over Solidity?",
                ],
            }

        try:
            # Retrieve relevant context
            context_result = self.context_tool.execute(
                query=question,
                n_results=5,
                content_type="all",
                rerank=True,
            )

            references = []
            context_text = ""

            if "contexts" in context_result:
                for ctx in context_result["contexts"]:
                    references.append({
                        "title": ctx["metadata"].get("title", "Reference"),
                        "source": ctx["source"],
                        "relevance": f"Relevance score: {ctx['relevance_score']:.2f}",
                    })
                    context_text += f"\n--- Reference: {ctx['source']} ---\n{ctx['content'][:1200]}\n"

            # Build prompt
            user_prompt = self._build_prompt(
                question=question,
                code_context=code_context,
                question_type=question_type,
                context_text=context_text,
            )

            # Generate answer
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

            response = self._call_llm(
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
            )

            # Parse response
            answer, code_examples = self._parse_response(response)

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

    def _parse_response(self, response: str) -> tuple[str, list[dict]]:
        """Parse answer and code examples from response."""
        code_examples = []

        # Extract code blocks
        code_pattern = r"```(?:rust)?\s*([\s\S]*?)```"
        matches = re.findall(code_pattern, response)

        for i, match in enumerate(matches):
            code_examples.append({
                "description": f"Example {i + 1}",
                "code": match.strip(),
            })

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
