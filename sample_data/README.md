## To import the dataset on MongoDB for doing a Bulk Index with the test_endpoints

1. Import the data
```bash
mongoimport --uri "mongodb://mongo:<password>@localhost:27017/b2b3?replicaSet=rs0&authSource=admin" \
  --db b2b3 \
  --collection listingsAndReviews \
  --file listingsAndReviews.json
```

2. Execute the tests
```bash
python test_endpoints.py
```