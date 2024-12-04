## To import the dataset on MongoDB for doing a Bulk Index with the test_endpoints

### 1. Import the data
```bash
mongoimport --uri "mongodb://mongo:<password>@localhost:27017/b2b3?replicaSet=rs0&authSource=admin" \
  --db b2b3 \
  --collection listingsAndReviews \
  --file listingsAndReviews.json
```

### 2. Start the service
check at the readme how to start the service

### 3. Execute the tests
```bash
python test_endpoints.py
```

#### Example of the output

```bash
python test_endpoints.py
2024-12-03 22:06:47,599 - INFO - Starting API endpoint tests
2024-12-03 22:06:47,599 - INFO - Testing POST /index
2024-12-03 22:06:47,669 - INFO - HTTP Request: POST http://localhost:8000/index "HTTP/1.1 200 OK"
2024-12-03 22:06:47,670 - INFO - Status code: 200
2024-12-03 22:06:47,670 - INFO - ✓ Listing indexed successfully
2024-12-03 22:06:47,670 - INFO - Testing POST /search
2024-12-03 22:06:47,744 - INFO - HTTP Request: POST http://localhost:8000/search "HTTP/1.1 200 OK"
2024-12-03 22:06:47,744 - INFO - Status code: 200
2024-12-03 22:06:47,744 - INFO - ✓ Search completed successfully
2024-12-03 22:06:47,744 - INFO - Testing PUT /documents/d1c29a5e-181c-45a0-a5e4-c82cd742ff3a
2024-12-03 22:06:47,799 - INFO - HTTP Request: PUT http://localhost:8000/documents/d1c29a5e-181c-45a0-a5e4-c82cd742ff3a "HTTP/1.1 200 OK"
2024-12-03 22:06:47,799 - INFO - Status code: 200
2024-12-03 22:06:47,800 - INFO - ✓ Listing updated successfully
2024-12-03 22:06:47,800 - INFO - Testing POST /bulk-index
2024-12-03 22:06:47,837 - INFO - HTTP Request: POST http://localhost:8000/bulk-index "HTTP/1.1 200 OK"
2024-12-03 22:06:47,837 - INFO - Status code: 200
2024-12-03 22:06:47,837 - INFO - ✓ Bulk index completed successfully
2024-12-03 22:06:47,837 - INFO - Testing POST /search
2024-12-03 22:06:47,884 - INFO - HTTP Request: POST http://localhost:8000/search "HTTP/1.1 200 OK"
2024-12-03 22:06:47,884 - INFO - Status code: 200
2024-12-03 22:06:47,884 - INFO - ✓ Search for 'apartments in Brooklyn with wifi' completed successfully
2024-12-03 22:06:47,885 - INFO - Testing POST /search
2024-12-03 22:06:47,929 - INFO - HTTP Request: POST http://localhost:8000/search "HTTP/1.1 200 OK"
2024-12-03 22:06:47,930 - INFO - Status code: 200
2024-12-03 22:06:47,930 - INFO - ✓ Search for 'luxury homes with pool' completed successfully
2024-12-03 22:06:47,930 - INFO - Testing POST /search
2024-12-03 22:06:47,985 - INFO - HTTP Request: POST http://localhost:8000/search "HTTP/1.1 200 OK"
2024-12-03 22:06:47,986 - INFO - Status code: 200
2024-12-03 22:06:47,986 - INFO - ✓ Search for 'affordable rooms near public transport' completed successfully
2024-12-03 22:06:47,986 - INFO - Testing POST /search
2024-12-03 22:06:48,033 - INFO - HTTP Request: POST http://localhost:8000/search "HTTP/1.1 200 OK"
2024-12-03 22:06:48,034 - INFO - Status code: 200
2024-12-03 22:06:48,034 - INFO - ✓ Search for 'entire apartment with kitchen and air conditioning' completed successfully
2024-12-03 22:06:48,034 - INFO - Testing POST /search
2024-12-03 22:06:48,085 - INFO - HTTP Request: POST http://localhost:8000/search "HTTP/1.1 200 OK"
2024-12-03 22:06:48,086 - INFO - Status code: 200
2024-12-03 22:06:48,086 - INFO - ✓ Search for 'highly rated places with good location' completed successfully
2024-12-03 22:06:48,086 - INFO - Testing DELETE /documents/d1c29a5e-181c-45a0-a5e4-c82cd742ff3a
2024-12-03 22:06:48,091 - INFO - HTTP Request: DELETE http://localhost:8000/documents/d1c29a5e-181c-45a0-a5e4-c82cd742ff3a "HTTP/1.1 200 OK"
2024-12-03 22:06:48,091 - INFO - Status code: 200
2024-12-03 22:06:48,091 - INFO - ✓ Listing deleted successfully
2024-12-03 22:06:48,091 - INFO - 
Test Summary:
2024-12-03 22:06:48,091 - INFO - ==================================================
2024-12-03 22:06:48,091 - INFO - Index single listing: ✓ Passed
2024-12-03 22:06:48,091 - INFO - Search listings: ✓ Passed
2024-12-03 22:06:48,091 - INFO - Update listing: ✓ Passed
2024-12-03 22:06:48,091 - INFO - Bulk index listings: ✓ Passed
2024-12-03 22:06:48,091 - INFO - Search: apartments in Brooklyn with wifi: ✓ Passed
2024-12-03 22:06:48,091 - INFO - Search: luxury homes with pool: ✓ Passed
2024-12-03 22:06:48,091 - INFO - Search: affordable rooms near public transport: ✓ Passed
2024-12-03 22:06:48,091 - INFO - Search: entire apartment with kitchen and air conditioning: ✓ Passed
2024-12-03 22:06:48,091 - INFO - Search: highly rated places with good location: ✓ Passed
2024-12-03 22:06:48,091 - INFO - Delete listing: ✓ Passed
2024-12-03 22:06:48,091 - INFO - ==================================================
2024-12-03 22:06:48,091 - INFO - Total Tests: 10
2024-12-03 22:06:48,091 - INFO - Passed: 10
2024-12-03 22:06:48,091 - INFO - Failed: 0
2024-12-03 22:06:48,091 - INFO - Success Rate: 100.0%
```
