#!/usr/bin/env python3
import asyncio
import httpx
import json
import logging
from typing import Dict, Any, Tuple
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API Configuration
API_BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

async def test_endpoint(
    client: httpx.AsyncClient,
    method: str,
    endpoint: str,
    data: Dict[str, Any] = None,
    expected_status: int = 200
) -> Tuple[bool, Dict[str, Any]]:
    """Test an endpoint and return whether it succeeded and the response data"""
    try:
        logger.info(f"Testing {method} {endpoint}")
        if data:
            logger.debug(f"Request data: {json.dumps(data, indent=2)}")
        
        response = await client.request(
            method=method,
            url=f"{API_BASE_URL}{endpoint}",
            json=data,
            headers=HEADERS,
            timeout=30.0
        )
        
        logger.info(f"Status code: {response.status_code}")
        response_data = response.json() if response.text else {}
        logger.debug(f"Response: {json.dumps(response_data, indent=2)}")
        
        if response.status_code != expected_status:
            logger.error(f"Unexpected status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False, {}
            
        return True, response_data
    except Exception as e:
        logger.error(f"Error testing {method} {endpoint}: {str(e)}")
        return False, {}

async def verify_search_results(
    client: httpx.AsyncClient,
    query: str,
    expected_content: str = None,
    min_results: int = 1
) -> bool:
    """Verify search results contain expected content"""
    success, response_data = await test_endpoint(
        client, "POST", "/search",
        data={"text": query, "max_results": 5}
    )
    
    if not success:
        return False
        
    results = response_data.get("results", [])
    logger.info(f"Found {len(results)} results for query: '{query}'")
    
    if len(results) < min_results:
        logger.error(f"Expected at least {min_results} results, got {len(results)}")
        return False
        
    if expected_content:
        found = False
        for result in results:
            content = result.get("content", "").lower()
            if expected_content.lower() in content:
                found = True
                logger.info(f"Found matching content: {content[:100]}...")
                break
        
        if not found:
            logger.error(f"Expected content '{expected_content}' not found in results")
            return False
    
    # Log some details about the results
    for i, result in enumerate(results):
        logger.info(f"Result {i + 1}:")
        logger.info(f"  Score: {result.get('score', 'N/A')}")
        logger.info(f"  Content: {result.get('content', '')[:100]}...")
        if result.get('metadata'):
            logger.info(f"  Metadata: {json.dumps(result.get('metadata'), indent=2)}")
    
    return True

async def run_tests():
    """Run all endpoint tests"""
    async with httpx.AsyncClient() as client:
        test_results = []
        total_tests = 0
        passed_tests = 0
        
        logger.info("Starting API endpoint tests")
        
        # Test 1: Index a single Airbnb listing
        total_tests += 1
        doc_id = str(uuid.uuid4())
        index_data = {
            "id": doc_id,
            "content": "Charming apartment in Brooklyn with WiFi and Air conditioning. Perfect for 2 guests, close to public transport.",
            "metadata": {
                "name": "Cozy Brooklyn Apartment",
                "property_type": "Apartment",
                "room_type": "Entire home/apt",
                "neighborhood": "Brooklyn",
                "price": 150.00,
                "amenities": ["Wifi", "Air conditioning", "Kitchen"],
                "bedrooms": 1,
                "bathrooms": 1,
                "max_guests": 2
            }
        }
        success, _ = await test_endpoint(
            client, "POST", "/index",
            data=index_data
        )
        test_results.append(("Index single listing", success))
        if success:
            passed_tests += 1
            logger.info("✓ Listing indexed successfully")
        
        # Test 2: Search for the indexed listing
        total_tests += 1
        success = await verify_search_results(
            client,
            "apartment in Brooklyn with wifi",
            expected_content="brooklyn",
            min_results=1
        )
        test_results.append(("Search listings", success))
        if success:
            passed_tests += 1
            logger.info("✓ Search completed successfully")
        
        # Test 3: Update the listing
        total_tests += 1
        update_data = {
            "content": "Updated Brooklyn apartment with WiFi, Air conditioning, and newly renovated kitchen. Close to subway, perfect for 2-3 guests.",
            "metadata": {
                "name": "Cozy Brooklyn Apartment",
                "property_type": "Apartment",
                "room_type": "Entire home/apt",
                "neighborhood": "Brooklyn",
                "price": 165.00,
                "amenities": ["Wifi", "Air conditioning", "Kitchen", "Subway access"],
                "bedrooms": 1,
                "bathrooms": 1,
                "max_guests": 3,
                "updated_at": datetime.now().isoformat()
            }
        }
        success, _ = await test_endpoint(
            client, "PUT", f"/documents/{doc_id}",
            data=update_data
        )
        test_results.append(("Update listing", success))
        if success:
            passed_tests += 1
            logger.info("✓ Listing updated successfully")
            
            # Verify the update by searching
            success = await verify_search_results(
                client,
                "renovated kitchen subway",
                expected_content="renovated",
                min_results=1
            )
            if success:
                logger.info("✓ Updated content found in search results")
        
        # Test 4: Bulk index Airbnb listings
        total_tests += 1
        bulk_index_data = {
            "collection_name": "listingsAndReviews",
            "aggregation_pipeline": [
                                        {
                                "$project": {
                                    "_id": 1,
                                    "content": {
                                        "$concat": [
                                            "$name", " - ",
                                            {"$ifNull": ["$summary", ""]}, " ",
                                            {"$ifNull": ["$description", ""]}, " ",
                                            {"$ifNull": ["$neighborhood_overview", ""]}
                                        ]
                                    },
                                    "metadata": {
                                        "name": "$name",
                                        "property_type": "$property_type",
                                        "room_type": "$room_type",
                                        "neighborhood": "$address.suburb",
                                        "price": {"$ifNull": ["$price", 0]},
                                        "amenities": "$amenities",
                                        "bedrooms": {"$ifNull": ["$bedrooms", 0]},
                                        "bathrooms": {"$ifNull": ["$bathrooms", 0]},
                                        "max_guests": "$accommodates",
                                        "host": {
                                            "name": "$host.host_name",
                                            "is_superhost": "$host.host_is_superhost"
                                        },
                                        "review_scores": "$review_scores"
                                    }
                                }
                            },{
                                "$limit": 100
                            }
            ],
            "id_field": "_id",
            "content_field": "content",
            "metadata_fields": ["metadata"],
            "batch_size": 100
        }
        success, response = await test_endpoint(
            client, "POST", "/bulk-index",
            data=bulk_index_data
        )
        indexed_count = response.get('indexed_count', 0)
        test_results.append(("Bulk index listings", success and indexed_count > 0))
        if success:
            if indexed_count > 0:
                logger.info(f"✓ Bulk index completed successfully - Indexed {indexed_count} documents")
                passed_tests += 1
            else:
                logger.error("✗ Bulk index completed but no documents were indexed")
                if response.get('errors'):
                    logger.error("Errors during bulk indexing:")
                    for error in response.get('errors')[:5]:  # Show first 5 errors
                        logger.error(f"  - {error}")
        
        # Test 5: Search with various queries
        search_queries = [
            ("apartments in Brooklyn with wifi", "brooklyn", 1),
            ("apartment pool luxury", "pool", 0),  # Optional test
            ("rooms near transport", "transport", 0),  # Optional test
            ("apartment with kitchen", "kitchen", 1),
            ("apartment good location", None, 0)  # Optional test
        ]
        
        for query, expected_content, min_results in search_queries:
            total_tests += 1
            success = await verify_search_results(
                client,
                query,
                expected_content=expected_content,
                min_results=min_results
            )
            test_results.append((f"Search: {query}", success))
            if success:
                passed_tests += 1
                logger.info(f"✓ Search for '{query}' completed successfully")
        
        # Test 6: Delete the test listing
        total_tests += 1
        success, _ = await test_endpoint(
            client, "DELETE", f"/documents/{doc_id}"
        )
        test_results.append(("Delete listing", success))
        if success:
            passed_tests += 1
            logger.info("✓ Listing deleted successfully")
            
            # Verify deletion by searching
            success, response = await test_endpoint(
                client, "POST", "/search",
                data={"text": "renovated kitchen subway", "max_results": 5}
            )
            results = response.get("results", [])
            deleted_found = any(r.get("id") == doc_id for r in results)
            if not deleted_found:
                logger.info("✓ Deleted listing no longer appears in search results")
            else:
                logger.error("✗ Deleted listing still appears in search results")
        
        # Print summary
        logger.info("\nTest Summary:")
        logger.info("=" * 50)
        for test_name, result in test_results:
            status = "✓ Passed" if result else "✗ Failed"
            logger.info(f"{test_name}: {status}")
        
        logger.info("=" * 50)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {total_tests - passed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(run_tests()) 