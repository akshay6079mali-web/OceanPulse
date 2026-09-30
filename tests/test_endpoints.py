import requests

BASE_URL = 'http://127.0.0.1:8000'

def run():
    print("Testing unauthenticated access...")
    r = requests.get(f'{BASE_URL}/api/v1/slicks')
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    print("Unauthenticated access blocked successfully.")
    
    print("Authenticating...")
    token = requests.post(f'{BASE_URL}/token', data={'username':'admin', 'password':'password123'}).json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    
    print("Testing authenticated /api/v1/slicks...")
    r = requests.get(f'{BASE_URL}/api/v1/slicks', headers=headers)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    
    print("Testing authenticated /api/v1/incois/forecast...")
    r = requests.get(f'{BASE_URL}/api/v1/incois/forecast', headers=headers)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    
    print("Verification complete. All endpoints secured and responding correctly.")

if __name__ == '__main__':
    run()
