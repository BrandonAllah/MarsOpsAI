
import os
from dotenv import load_dotenv
from google import genai

# Load our private API key from .env
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

# Connect to Gemma 4
client = genai.Client(api_key=api_key) if api_key else None


def get_mission_advice(battery, samples_collected, rover_x, rover_y, remaining_samples,
                       objective="Collect Samples", battery_capacity=100,
                       credits=0, at_base=False):
    """
    Ask Gemma to analyze the rover's current mission status.
    """

    prompt = f"""
    You are the AI mission copilot for a simulated Mars rover.

    CURRENT MISSION DATA:
    Battery: {battery:.1f} / {battery_capacity}
    Samples collected: {samples_collected}/3
    Objective: {objective}
    At base: {at_base}
    Research credits: {credits}
    Base position: (450, 900)
    Rover position: ({rover_x}, {rover_y})
    Remaining sample coordinates: {remaining_samples}

    Give a short mission briefing with:
    1. Current mission status.
    2. Recommended next action.
    3. Any battery or navigation concerns.

    A mission is complete only after returning to base with all three samples.
    The base recharges the battery.
    Use only the provided simulation data.
    Do not invent terrain maps, scientific discoveries,
    hazards, or mission equipment.

    Keep your response under 75 words.
    """

    if client is None:
        raise RuntimeError("Gemma API key is not configured")
    response = client.models.generate_content(
        model="gemma-4-26b-a4b-it",
        contents=prompt
    )

    return (response.text or "No mission advice was generated.").strip()

def get_discovery_explanation(discovery, more=False):
    """Ask Gemma to explain supplied facts, without adding unsourced claims."""
    prompt = f"""
    Explain the following Mars discovery for a game player in under 65 words.
    {'Offer a different angle using only the same facts.' if more else 'Explain why it matters.'}
    Use only the facts below. Clearly distinguish observations from hypotheses.
    Never invent discoveries, evidence, instruments, experiments, or conclusions.
    If the facts do not establish something, say it is unknown. Do not claim life was found.

    Discovery: {discovery.name}
    Verified description: {discovery.description}
    Scientific significance and uncertainty: {discovery.significance}
    NASA source: {discovery.source_url}
    """
    if client is None:
        raise RuntimeError("Gemma API key is not configured")
    response = client.models.generate_content(model="gemma-4-26b-a4b-it", contents=prompt)
    text = (response.text or "").strip()
    if not text:
        raise ValueError("Empty discovery explanation")
    return text


def discovery_briefing(discovery, more=False):
    """Fall back to the local, NASA-sourced facts if the AI cannot respond."""
    try:
        explanation = get_discovery_explanation(discovery, more)
        return f"AI explanation: {discovery.name}\n\n{explanation}"
    except Exception:
        return (f"NASA facts (AI unavailable): {discovery.name}\n\n"
                f"{discovery.description} {discovery.significance}")
