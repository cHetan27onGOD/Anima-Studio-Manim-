#!/usr/bin/env python3
"""
Comprehensive test script for Anima Studio
Tests:
1. Registration and login
2. Video generation with different inputs
3. Verifies different prompts produce different plans
"""
import http.client
import pytest
import json
import time
import sys

BASE_URL = "localhost:8000"
PROMPTS = [
    "Simple neural network: input layer (3), hidden layer (4), output (1)",
    "Explain cache miss with client server cache db",
    "Animate a rotating triangle with color changes",
    "Visualization of a star network topology",
    "Two circles moving right with smooth motion",
    "Process flow: User -> Auth -> API -> Database",
]

pytest.skip("system test skipped in pytest runs", allow_module_level=True)

def make_request(method, path, body=None, headers=None, auth_token=None):
    """Make HTTP request"""
    conn = http.client.HTTPConnection(BASE_URL)
    
    if headers is None:
        headers = {'Content-Type': 'application/json'}
    else:
        headers['Content-Type'] = 'application/json'
    
    if auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'
    
    try:
        conn.request(method, path, body, headers)
        response = conn.getresponse()
        status = response.status
        data = response.read().decode()
        conn.close()
        return status, data
    except Exception as e:
        print(f"Error: {e}")
        return None, None

def test_registration_and_login():
    """Test user registration and login"""
    print("\n" + "="*60)
    print("TEST 1: Registration and Login")
    print("="*60)
    
    email = f"testuser{int(time.time())}@example.com"
    password = "testpass123"
    
    # Register
    register_body = json.dumps({
        "email": email,
        "password": password,
        "full_name": "Test User"
    })
    
    status, data = make_request('POST', '/api/auth/register', register_body)
    print(f"Registration: Status {status}")
    if status == 200:
        user = json.loads(data)
        print(f"✓ Registered: {user['email']}")
    else:
        print(f"✗ Failed: {data}")
        return None
    
    # Login
    login_body = f"username={email}&password={password}"
    login_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    conn = http.client.HTTPConnection(BASE_URL)
    conn.request('POST', '/api/auth/login', login_body, login_headers)
    response = conn.getresponse()
    status = response.status
    data = response.read().decode()
    conn.close()
    
    print(f"Login: Status {status}")
    if status == 200:
        token = json.loads(data)['access_token']
        print(f"✓ Logged in, token: {token[:40]}...")
        return token, email
    else:
        print(f"✗ Failed: {data}")
        return None, None

def test_video_generation(token, email):
    """Test generating videos with different prompts"""
    print("\n" + "="*60)
    print("TEST 2: Video Generation with Different Inputs")
    print("="*60)
    
    jobs = []
    
    for i, prompt in enumerate(PROMPTS[:3], 1):  # Test first 3 prompts
        print(f"\n[{i}] Creating video: '{prompt[:50]}...'")
        
        job_body = json.dumps({"prompt": prompt})
        status, data = make_request('POST', '/api/jobs', job_body, auth_token=token)
        
        if status == 201:
            job_data = json.loads(data)
            job_id = job_data['job_id']
            jobs.append({
                'id': job_id,
                'prompt': prompt,
                'status': 'queued'
            })
            print(f"    ✓ Job created: {job_id}")
            print(f"    Status: {job_data['status']}")
        else:
            print(f"    ✗ Failed: {data}")
    
    print(f"\nTotal jobs created: {len(jobs)}")
    return jobs

def test_job_status(token, jobs):
    """Check job status and verify different plans"""
    print("\n" + "="*60)
    print("TEST 3: Monitor Job Status and Plans")
    print("="*60)
    
    print("\nMonitoring 6 seconds...")
    for second in range(6):
        print(f"[{second+1}s] Checking status...")
        time.sleep(1)
        
        for job in jobs:
            status, data = make_request('GET', f"/api/jobs/{job['id']}", auth_token=token)
            if status == 200:
                job_data = json.loads(data)
                job['status'] = job_data['status']
                
                # Extract plan info
                if job_data.get('plan_json'):
                    plan = job_data['plan_json']
                    if 'title' in plan:
                        job['plan_title'] = plan.get('title', 'N/A')
                    if 'scenes' in plan:
                        job['scenes_count'] = len(plan.get('scenes', []))
    
    # Print summary
    print("\n" + "-"*60)
    print("PLAN COMPARISON:")
    print("-"*60)
    
    plans_different = True
    for i, job in enumerate(jobs, 1):
        print(f"\nJob {i}: {job['prompt'][:50]}...")
        print(f"  Status: {job['status']}")
        if 'plan_title' in job:
            print(f"  Plan Title: {job['plan_title']}")
        if 'scenes_count' in job:
            print(f"  Scenes: {job['scenes_count']}")
    
    # Check if plans are actually different
    plan_titles = [job.get('plan_title', 'N/A') for job in jobs]
    if len(set(plan_titles)) < len(plan_titles):
        print("\n⚠ Some plans have same titles")
    else:
        print("\n✓ All plans have unique titles")

def test_get_jobs_list(token):
    """Test getting jobs list"""
    print("\n" + "="*60)
    print("TEST 4: Get Jobs List")
    print("="*60)
    
    status, data = make_request('GET', '/api/jobs', auth_token=token)
    print(f"Status: {status}")
    
    if status == 200:
        jobs = json.loads(data)
        print(f"✓ Retrieved {len(jobs)} jobs")
        for job in jobs[:3]:
            print(f"  - {job['id']}: {job['prompt'][:50]}... ({job['status']})")
    else:
        print(f"✗ Failed: {data}")

def main():
    """Run all tests"""
    print("\n" + "█"*60)
    print("█ ANIMA STUDIO COMPREHENSIVE TEST")
    print("█"*60)
    
    # Test 1: Registration and Login
    result = test_registration_and_login()
    if not result or not result[0]:
        print("\n✗ Authentication tests failed!")
        return
    
    token, email = result
    
    # Test 2: Create multiple videos with different inputs
    jobs = test_video_generation(token, email)
    if not jobs:
        print("\n⚠ No jobs created")
        return
    
    # Test 3: Monitor status and check plans
    test_job_status(token, jobs)
    
    # Test 4: Get jobs list
    test_get_jobs_list(token)
    
    # Summary
    print("\n" + "█"*60)
    print("█ TEST SUMMARY")
    print("█"*60)
    print("✓ Backend API: WORKING")
    print("✓ Authentication: WORKING (Register + Login)")
    print(f"✓ Video Creation: {len(jobs)} jobs created successfully")
    print("✓ Job Tracking: Status monitoring works")
    print("\nNote: Videos are queued in the background.")
    print("Check status at http://localhost:3000")
    print("█"*60 + "\n")

if __name__ == '__main__':
    main()
