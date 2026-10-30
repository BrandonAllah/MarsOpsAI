
from ai_copilot import get_mission_advice

print("Contacting MarsOps AI Copilot...")

advice = get_mission_advice(
    battery=85,
    samples_collected=1,
    rover_x=425,
    rover_y=275,
    remaining_samples=[(100, 300), (750, 450)]
)

print("\nMARSOPS AI COPILOT")
print("------------------------")
print(advice)
