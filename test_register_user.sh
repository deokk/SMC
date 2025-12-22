curl -X POST "http://localhost:8000/users/register" \
-H "Content-Type: application/json" \
-d '{
  "username": "testuser",
  "email": "test@example.com",
  "password": "testpassword"
}'