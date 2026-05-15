"""
llm_runner.py

Sends a prompt to an LLM and returns the extracted SQL string.

Supported models:
  Gemini (Google AI Studio):
    - gemini-2.5-flash       free tier
    - gemini-2.5-pro         free tier

  Together AI (OpenAI-compatible API):
    - qwen2.5-coder-32b      Qwen/Qwen2.5-Coder-32B-Instruct
    - qwen2.5-coder-7b       Qwen/Qwen2.5-Coder-7B-Instruct
    - qwen2.5-coder-72b      Qwen/Qwen2.5-Coder-72B-Instruct
    - llama-3.1-8b           meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
    - llama-3.3-70b          meta-llama/Llama-3.3-70B-Instruct-Turbo

Setup:
  pip install openai google-genai

  export TOGETHER_API_KEY="your_key_here"
  export GEMINI_API_KEY="your_key_here"

Usage:
    from src.llm_runner import call_llm
    sql = call_llm("qwen2.5-coder-32b", prompt)
"""

import os
import re
import time

# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------

MODELS = {
    # --- Gemini ---
    "gemini-2.5-flash": {
        "provider": "gemini",
        "model_id": "gemini-2.5-flash",
    },
    "gemini-2.5-pro": {
        "provider": "gemini",
        "model_id": "gemini-2.5-pro",
    },
    "gemini-2.0-flash": {
        "provider": "gemini",
        "model_id": "gemini-2.0-flash",
    },
    "gemini-2.0-flash-lite": {
        "provider": "gemini",
        "model_id": "gemini-2.0-flash-lite",
    },
    # --- Together AI: Llama ---
    "llama-3.1-8b": {
        "provider": "together",
        "model_id": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    },
    "llama-3.3-70b": {
        "provider": "together",
        "model_id": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    },
    # --- OpenRouter: Qwen (currently broken on OpenRouter — use when fixed) ---
    "qwen2.5-coder-32b": {
        "provider": "openrouter",
        "model_id": "qwen/qwen-2.5-coder-32b-instruct",
    },
    # --- OpenRouter: Llama (working) ---
    "llama-3.3-70b-or": {
        "provider": "openrouter",
        "model_id": "meta-llama/llama-3.3-70b-instruct",
    },
    "llama-3.1-8b-or": {
        "provider": "openrouter",
        "model_id": "meta-llama/llama-3.1-8b-instruct",
    },
}

# Temperature fixed at 0 across all runs (reproducibility requirement)
_TEMPERATURE = 0

# Retry on rate-limit errors (HTTP 429)
_MAX_RETRIES = 5
_RETRY_BASE_DELAY = 10  # seconds; doubles on each retry


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def call_llm(model_name: str, prompt: str) -> str:
    """
    Send a prompt to the specified model and return the cleaned SQL string.

    Args:
        model_name: Key from MODELS (e.g. 'qwen2.5-coder-32b').
        prompt    : Full prompt string from prompt_builder.build_prompt().

    Returns:
        SQL string with markdown fences stripped.
        Returns an empty string if the call fails after all retries.
    """
    if model_name not in MODELS:
        raise ValueError(
            f"Unknown model '{model_name}'. Available: {list(MODELS.keys())}"
        )

    config = MODELS[model_name]
    provider = config["provider"]

    if provider == "openrouter":
        raw = _call_openrouter(config["model_id"], prompt)
    elif provider == "together":
        raw = _call_together(config["model_id"], prompt)
    elif provider == "gemini":
        raw = _call_gemini(config["model_id"], prompt)
    else:
        raise NotImplementedError(f"Provider '{provider}' is not implemented.")

    return extract_sql(raw)


def extract_sql(text: str) -> str:
    """
    Extract the SQL query from the LLM response, handling:
      - Qwen thinking blocks: <think>...</think> before the SQL
      - Markdown code fences: ```sql ... ``` or ``` ... ```
      - Clean responses: SELECT ... (returned as-is)
    """
    if not text:
        return ""

    # Strip Qwen-style thinking blocks (may appear before the SQL)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    if not text:
        return ""

    # Extract from markdown code fences if present
    fenced = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()

    return text.strip()


# ---------------------------------------------------------------------------
# Provider: OpenRouter
# ---------------------------------------------------------------------------

def _call_openrouter(model_id: str, prompt: str) -> str:
    """
    Call OpenRouter via its OpenAI-compatible API.
    Models with ':free' suffix are free with no credit card required.
    Get a key at https://openrouter.ai/keys
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("Run: pip install openai")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENROUTER_API_KEY environment variable is not set.\n"
            "Get a free key at https://openrouter.ai/keys\n"
            "Then run: export OPENROUTER_API_KEY='your_key_here'"
        )

    # Bounded HTTP time so a hung TLS/socket does not freeze the experiment loop.
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        timeout=180.0,
    )

    delay = _RETRY_BASE_DELAY
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=_TEMPERATURE,
                max_tokens=4096,
                extra_headers={"X-use-cache": "false"},  # disable OpenRouter response cache
            )
            return response.choices[0].message.content or ""

        except Exception as e:
            err_str = str(e)
            print("Error: ", err_str)
            el = err_str.lower()
            is_rate_limit = "429" in err_str or "rate" in el
            # Transient network / edge failures — same backoff as rate limits.
            is_transient = (
                is_rate_limit
                or "connection" in el
                or "timeout" in el
                or "connecterror" in el
                or "network" in el
                or "ssl" in el
                or "reset" in el
            )

            if is_transient and attempt < _MAX_RETRIES:
                reason = "Rate limit" if is_rate_limit else "Transient error"
                print(
                    f"  [OpenRouter] {reason} — waiting {delay}s "
                    f"(attempt {attempt}/{_MAX_RETRIES})"
                )
                time.sleep(delay)
                delay *= 2
            else:
                print(f"  [OpenRouter] Error on attempt {attempt}: {e}")
                return ""

    return ""


# ---------------------------------------------------------------------------
# Provider: Together AI
# ---------------------------------------------------------------------------

def _call_together(model_id: str, prompt: str) -> str:
    """
    Call Together AI's OpenAI-compatible chat endpoint.
    Together AI uses the same interface as OpenAI, just with a different base URL.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("Run: pip install openai")

    api_key = os.environ.get("TOGETHER_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "TOGETHER_API_KEY environment variable is not set.\n"
            "Get a key at https://api.together.ai\n"
            "Then run: export TOGETHER_API_KEY='your_key_here'"
        )

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.together.xyz/v1",
        timeout=180.0,
    )

    delay = _RETRY_BASE_DELAY
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=_TEMPERATURE,
                max_tokens=512,
            )
            return response.choices[0].message.content or ""

        except Exception as e:
            err_str = str(e)
            el = err_str.lower()
            is_rate_limit = "429" in err_str or "rate" in el
            is_transient = (
                is_rate_limit
                or "connection" in el
                or "timeout" in el
                or "connecterror" in el
            )
            if is_transient and attempt < _MAX_RETRIES:
                reason = "Rate limit" if is_rate_limit else "Transient error"
                print(
                    f"  [Together] {reason} — waiting {delay}s "
                    f"(attempt {attempt}/{_MAX_RETRIES})"
                )
                time.sleep(delay)
                delay *= 2
            else:
                print(f"  [Together] Error on attempt {attempt}: {e}")
                return ""

    return ""


# ---------------------------------------------------------------------------
# Provider: Gemini
# ---------------------------------------------------------------------------

def _call_gemini(model_id: str, prompt: str) -> str:
    """
    Call Google Gemini via the google-genai SDK (replaces deprecated google-generativeai).
    """
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        raise ImportError("Run: pip install google-genai")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY environment variable is not set.\n"
            "Get a free key at https://aistudio.google.com/apikey\n"
            "Then run: export GEMINI_API_KEY='your_key_here'"
        )

    client = genai.Client(
        api_key=api_key,
        http_options=genai_types.HttpOptions(timeout=300_000),  # 5 minutes (ms)
    )

    delay = _RETRY_BASE_DELAY
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=_TEMPERATURE,
                    candidate_count=1,
                ),
            )
            return response.text or ""

        except Exception as e:
            err_str = str(e)
            print("Error: ", err_str)
            is_rate_limit = "429" in err_str or "quota" in err_str.lower()

            if is_rate_limit and attempt < _MAX_RETRIES:
                print(
                    f"  [Gemini] Rate limit — waiting {delay}s "
                    f"(attempt {attempt}/{_MAX_RETRIES})"
                )
                time.sleep(delay)
                delay *= 2
            else:
                print(f"  [Gemini] Error on attempt {attempt}: {e}")
                return ""

    return ""
