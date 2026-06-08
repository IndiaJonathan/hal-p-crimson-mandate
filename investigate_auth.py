#!/usr/bin/env python3
import requests, re, json

# Check main page
r = requests.get('https://crimsonmandate.com/', timeout=10)
content = r.text
print('Main page status:', r.status_code)
print('Content length:', len(content))

# Find script tags
scripts = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
print('Inline scripts:', len(scripts))
for i, s in enumerate(scripts[:3]):
    print(f'Script {i}:', s[:300])

# Find src attributes
srcs = re.findall(r'src="([^"]+)"', content)
print('External sources:', srcs[:10])

# Check if there's an API endpoint for WS token
token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIwYThhMmZmNS0xYjkzLTQ0YzMtOTk0Yy02ODkxZTAwNzZkNzIiLCJzZXNzaW9uSWQiOiIzZWNhMGQ5Mi05ZmI3LTQ2NTEtODRjZS1iNjk0MDE3YjA0ZGQiLCJpYXQiOjE3ODA4NTE0ODgsImV4cIjoxNzgxNDU2Mjg4fQ._RZ527WGd_CF4uUVGbaiW13WQmXQt6puJG4D7HxG2J8'

# Try to find API docs or OpenAPI spec
for path in ['/api.json', '/openapi.json', '/api/docs', '/swagger.json']:
    try:
        r2 = requests.get(f'https://crimsonmandate.com{path}', timeout=5)
        print(f'{path}: {r2.status_code} {r2.text[:200]}')
    except:
        pass

# Try to get a WebSocket token via a login + immediate API call
# Login and immediately try to call various endpoints
login = requests.post('https://crimsonmandate.com/api/auth/login',
    json={'email': 'halp@burk-dashboards.com', 'password': 'Test1234!'}, timeout=15)
data = login.json()
if data.get('success'):
    t = data['data']['token']
    sid = data['data']['sessionId']
    print(f'\nGot token: {t[:50]}...')
    print(f'SessionId: {sid}')

    # Try various game endpoints
    for path in ['/api/game/join', '/api/mmo/join', '/api/world/join', '/api/game/start']:
        try:
            r3 = requests.post(f'https://crimsonmandate.com{path}',
                headers={'Authorization': f'Bearer {t}'},
                json={}, timeout=5)
            print(f'{path}: {r3.status_code} {r3.text[:200]}')
        except Exception as e:
            print(f'{path}: ERROR {e}')
