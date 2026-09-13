import os
import sys
from tools.browser_agent import AutonomousBrowserAgent

agent = AutonomousBrowserAgent()

plan = {
    'steps': [
        {'action': 'click', 'text': 'Individual', 'description': 'Individual radio option'},
        {'action': 'fill', 'selector': 'input#1240b1f2-3f31-4fa4-b5f9-d8aa766222ef', 'value': 'MUKILARASU S', 'description': 'Full Name'},
        {'action': 'fill', 'selector': 'input[type=\"email\"]', 'value': 'mukilarasu55@gmail.com', 'description': 'Email Address'},
        {'action': 'fill', 'selector': 'input#704a50cc-8005-46a3-bec3-969570d243ff', 'value': '+91-9080030538', 'description': 'Phone Number'},
        {'action': 'fill', 'selector': 'input#54e3a8a6-2f01-4c3b-96d2-49e6bb2df540', 'value': 'VSB-Engineering College, Karur', 'description': 'College'},
        {'action': 'click', 'text': 'Next', 'description': 'Next Button'}
    ]
}

print('[*] Launching AutonomousBrowserAgent (Headed mode)...')
res = agent.execute_web_mission('https://enter.fundmycrazy.com/', plan, headless=False)
print('[*] Status:', res['status'])
print('[*] Steps completed:', res['steps_completed'])
if res['screenshot']:
    print('[*] Proof screenshot:', res['screenshot'])
if res['error']:
    print('[*] Error:', res['error'])
