"""
Reviewer Agent - A critic agent for auditing and providing feedback on task outputs.

This agent implements the Reviewer role in a Doer-Critic self-correction loop,
analyzing outputs for logic flaws, efficiency issues, and accuracy problems.
"""

from typing import Optional

from pydantic import Field

from app.agent.base import BaseAgent
from app.llm import LLM
from app.logger import logger
from app.schema import AgentState, Message

REVIEWER_SYSTEM_PROMPT = """You are a senior software auditor and code reviewer with expertise in:
- Logic correctness and edge case analysis
- Code efficiency and performance optimization
- Best practices and design patterns
- Security vulnerabilities
- Error handling and robustness

Your role is to critically analyze outputs from other agents and provide constructive feedback.

## Chain-of-Thought Review Process

**BEFORE grading, systematically analyze using these questions:**

### 1. Logic & Correctness
- Does the code/solution actually solve the stated problem?
- Are there any logical errors or flaws in the approach?
- What happens with edge cases: empty inputs, null values, extremely large inputs?
- Are array indices within bounds? Do loops terminate correctly?

### 2. Error Handling & Robustness
- What can go wrong? (file not found, network errors, invalid input types)
- Are errors caught and handled gracefully?
- Are error messages helpful for debugging?
- Does the code fail safely or cause cascading failures?

### 3. Quality & Best Practices
- Is the code readable with clear variable names?
- Are there proper comments/docstrings?
- Does it follow language conventions?
- Is the approach efficient or unnecessarily complex?

### 4. Security & Safety
- Any injection vulnerabilities (SQL, command, etc.)?
- Is user input validated and sanitized?
- Are credentials or sensitive data exposed?
- Are permissions/access controls appropriate?

### 5. Testing & Verification
- Are there tests? Do they cover edge cases?
- Can the solution be easily tested?
- Is there evidence the code was actually run and verified?

## Grading Standard

**PASS**: Code meets professional standards, handles edge cases, has error handling, and is production-ready (or close)

**FAIL**: Code has logic errors, missing error handling, security issues, or fails basic test cases

## Output Format

**THINK STEP-BY-STEP** (show your analysis):
[Walk through your reasoning using the framework above]

**GRADE: PASS** or **GRADE: FAIL**

**ISSUES FOUND:**
1. [Specific issue with details - cite line numbers or examples]
2. [Another specific issue]
3. [Third issue if applicable]

**SUGGESTIONS:**
- [Concrete improvement recommendation]
- [Alternative approach if needed]

**SUMMARY:**
[One-sentence overall assessment]

Be strict but fair. Thoughtful analysis produces better feedback.
"""


class Reviewer(BaseAgent):
    """
    Reviewer/Critic agent for auditing task outputs.

    Provides structured feedback with PASS/FAIL grades and specific improvement suggestions.
    """

    name: str = "Reviewer"
    description: str = (
        "A senior auditor agent that reviews outputs for quality, correctness, and best practices"
    )

    system_prompt: str = REVIEWER_SYSTEM_PROMPT
    next_step_prompt: Optional[str] = None

    max_steps: int = 1  # Reviewer only needs one step to provide feedback

    async def step(self) -> str:
        """
        Execute a single review step.

        Returns:
            Review feedback with grade and specific issues/suggestions.
        """
        if not self.memory.messages:
            return "No content to review"

        # Get the last user message (which should contain the output to review)
        last_message = self.memory.messages[-1]
        if last_message.role != "user":
            return "Expected user message with content to review"

        # Ask LLM for review
        system_msg = Message.system_message(self.system_prompt)

        try:
            response = await self.llm.ask(
                messages=[last_message], system_msgs=[system_msg], stream=False
            )

            # llm.ask() returns a string directly, not an object with .content
            review_content = response if response else "No review generated"

            # Add review to memory
            self.update_memory("assistant", review_content)

            # Mark as finished after one review
            self.state = AgentState.FINISHED

            return review_content

        except Exception as e:
            logger.error(f"Reviewer error: {e}")
            return f"Review failed: {str(e)}"

    def extract_grade(self, review_text: str) -> str:
        """
        Extract PASS/FAIL grade from review text.

        Args:
            review_text: The review content

        Returns:
            "PASS", "FAIL", or "UNKNOWN"
        """
        review_upper = review_text.upper()

        if "GRADE: PASS" in review_upper or "**GRADE: PASS**" in review_upper:
            return "PASS"
        elif "GRADE: FAIL" in review_upper or "**GRADE: FAIL**" in review_upper:
            return "FAIL"
        else:
            # Default to PASS if unclear (optimistic)
            logger.warning("Could not determine grade from review, defaulting to PASS")
            return "PASS"
