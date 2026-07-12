#!/bin/bash
curl -s -X POST "http://localhost:8999/api/auth/signup" -H "Content-Type: application/json" -d '{"full_name": "Test User", "email": "test@example.com", "password": "password123"}' > signup.json
cat signup.json
curl -s -X POST "http://localhost:8999/api/auth/login" -H "Content-Type: application/x-www-form-urlencoded" -d "username=test@example.com&password=password123" > login.json
TOKEN=$(cat login.json | grep -o '"access_token": "[^"]*' | grep -o '[^"]*$')
cat login.json
curl -s -X GET "http://localhost:8999/api/farmers/me" -H "Authorization: Bearer $TOKEN" > me.json
cat me.json
