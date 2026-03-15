from app.services.llm import generate_plan, LLMQuotaExceededError
import app.services.llm as llm

# monkey-patch to simulate quota error

def fake_call(prompt, hint=None):
    raise LLMQuotaExceededError('simulated quota exceeded')

llm.call_combined_llm_planner = fake_call

plan = generate_plan('This is a test prompt that should trigger quota handling')
print('Plan title:', plan.title)
print('Rate limited flag:', plan.rate_limited)
print('Scenes:', len(plan.scenes))
