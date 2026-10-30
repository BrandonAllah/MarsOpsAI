
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


# ======================================
# MARSOPS AI - GEMMA 4 COPILOT
# ======================================

load_dotenv()

MODEL_NAME = "gemma-4-26b-a4b-it"
API_TIMEOUT_MS = 90000

api_key = os.getenv("GEMINI_API_KEY")

client = None

if api_key:
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=API_TIMEOUT_MS,
            retry_options=types.HttpRetryOptions(
                attempts=2,
                initial_delay=1,
                max_delay=2,
                http_status_codes=[500, 502, 503, 504]
            )
        )
    )


class CopilotResponse(str):
    """String-compatible response carrying its online/offline state to the UI."""
    def __new__(cls, text, offline=False):
        result = super().__new__(cls, text)
        result.offline = offline
        return result


def offline_reason(error):
    """Return a safe, user-facing summary without request or credential details."""
    code = getattr(error, "code", None)
    if code == 504 or isinstance(error, TimeoutError):
        return "The AI service timed out. Try again shortly."
    if code in (500, 502, 503):
        return "The AI service is temporarily unavailable. Try again shortly."
    if code == 429:
        return "The AI service is rate-limited. Wait before trying again."
    if code in (401, 403):
        return "The AI service rejected the request. Check API access."
    if client is None:
        return "No API key is configured."
    return "The AI service could not be reached. Try again shortly."


# ======================================
# ERROR LOGGING
# ======================================

def log_ai_error(context, error):
    """
    Log the error type and HTTP status
    without exposing API credentials.
    """

    error_type = type(error).__name__
    status_code = getattr(error, "code", None)

    print(
        f"[MarsOps AI] {context} failed | "
        f"Error: {error_type} | "
        f"HTTP status: {status_code or 'unknown'}"
    )


# ======================================
# GEMMA REQUEST HELPER
# ======================================

def generate_ai_response(prompt):
    """
    Contact Gemma 4.

    This function should be called from
    a background worker, not directly
    from the Pygame rendering loop.
    """

    if client is None:
        raise RuntimeError(
            "GEMINI_API_KEY is missing."
        )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    text = (response.text or "").strip()

    if not text:
        raise ValueError(
            "Gemma returned an empty response."
        )

    return text


# ======================================
# MISSION ADVICE
# ======================================

def get_mission_advice(
    battery,
    samples_collected,
    rover_x,
    rover_y,
    remaining_samples,
    objective="Collect Samples",
    battery_capacity=100,
    credits=0,
    at_base=False,
    required_samples=3,
    base_position=(450, 900)
):
    """
    Generate mission advice using
    the rover's current gameplay data.
    """

    prompt = f"""
You are the AI mission copilot for MarsOps AI,
a fictional Mars rover exploration game.

CURRENT MISSION DATA:

Battery: {battery:.1f}/{battery_capacity}
Samples collected: {samples_collected}/{required_samples}
Current objective: {objective}
Research credits: {credits}
Rover at base: {at_base}

ROVER POSITION:
({rover_x}, {rover_y})

BASE POSITION:
{base_position}

REMAINING SAMPLES:
{remaining_samples}

MISSION RULES:
- Collect the required geological samples.
- Return to base to complete the mission.
- The base recharges the rover.
- Research credits can purchase upgrades.

YOUR TASK:
Provide a brief, helpful mission update.

Include:
1. Current mission status.
2. Recommended next action.
3. Battery or navigation concerns.

IMPORTANT:
- Use only the supplied game data.
- Never invent terrain maps or obstacles.
- Do not claim routes are safe unless verified.
- Do not invent scientific discoveries.
- Do not invent rover equipment.
- Keep the response under 75 words.
"""

    try:
        return generate_ai_response(prompt)

    except Exception as error:
        log_ai_error("Mission briefing", error)

        if samples_collected >= required_samples:
            next_action = (
                "All required samples collected. "
                "Return to base to complete the mission."
            )
        elif battery < battery_capacity * 0.25:
            next_action = (
                "Battery is low. Consider returning "
                "to base for recharging."
            )
        else:
            next_action = (
                "Continue exploring and collecting "
                "the remaining samples."
            )

        return CopilotResponse(
            "MISSION CONTROL - OFFLINE MODE\n\n"
            f"Battery: {battery:.1f}/{battery_capacity}\n"
            f"Samples: {samples_collected}/{required_samples}\n"
            f"Objective: {objective}\n\n"
            f"Recommendation: {next_action}\n\n"
            "Gemma 4 is temporarily unavailable. " + offline_reason(error),
            offline=True
        )


# ======================================
# SCIENTIFIC DISCOVERY EXPLANATION
# ======================================

def get_discovery_explanation(
    discovery,
    more=False
):
    """
    Generate a scientific explanation
    using verified discovery records.
    """

    if more:
        instruction = (
            "Explain another interesting aspect "
            "of this discovery, using only "
            "the provided information."
        )
    else:
        instruction = (
            "Explain this discovery and why "
            "scientists consider it important."
        )

    prompt = f"""
You are the scientific AI copilot aboard
a simulated Mars exploration rover.

The player has investigated a real
Martian geological discovery.

DISCOVERY NAME:
{discovery.name}

VERIFIED DESCRIPTION:
{discovery.description}

SCIENTIFIC SIGNIFICANCE:
{discovery.significance}

NASA SOURCE:
{discovery.source_url}

TASK:
{instruction}

SCIENTIFIC RULES:
- Use only the verified facts provided.
- Distinguish observations from hypotheses.
- Never invent experiments or discoveries.
- Do not claim life on Mars is confirmed.
- Do not invent scientific conclusions.
- State uncertainty where appropriate.
- Keep the explanation under 65 words.
- Use clear, educational language.
"""

    return generate_ai_response(prompt)


# ======================================
# DISCOVERY BRIEFING WITH FALLBACK
# ======================================

def discovery_briefing(
    discovery,
    more=False
):
    """
    Provide a Gemma 4 explanation.

    If the request fails, provide the
    locally stored NASA discovery facts.
    """

    try:
        explanation = get_discovery_explanation(
            discovery,
            more
        )

        return CopilotResponse(
            "AI SCIENCE BRIEFING\n"
            f"{discovery.name}\n\n"
            f"{explanation}"
        )

    except Exception as error:

        log_ai_error(
            "Discovery briefing",
            error
        )

        return CopilotResponse(
            "NASA DISCOVERY INFORMATION\n"
            f"{discovery.name}\n\n"
            f"{discovery.description}\n\n"
            "Scientific significance:\n"
            f"{discovery.significance}\n\n"
            f"Source: {discovery.source_url}\n\n"
            "Gemma 4 is temporarily unavailable. "
            "Verified discovery information "
            "is shown instead. " + offline_reason(error),
            offline=True
        )
