import os
import requests
from dotenv import load_dotenv
import json
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

class PrintifyAPI:
    """
    A client for interacting with the Printify API.
    Handles authentication and common API requests.
    """
    def __init__(self, api_key=None, base_url="https://api.printify.com/v1"):
        self.api_key = api_key if api_key else os.getenv('PRINTIFY_API_TOKEN')
        self.base_url = base_url
        
        if not self.api_key:
            logger.error("🔴 CRITICAL ERROR: Printify API token is not provided or not set in .env.")
            raise ValueError("Printify API token must be provided or set as environment variable.")
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def _make_request(self, method, endpoint, json_data=None, params=None, files=None, timeout=30):
        """
        Internal helper to make API requests.
        """
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers, params=params, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=json_data, files=files, timeout=timeout)
            # Add other methods (PUT, DELETE) if needed
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()

        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error for {endpoint}: {http_err} - Response: {http_err.response.text}")
            return {"error": f"HTTP Error: {http_err.response.text}"}
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Connection error for {endpoint}: {conn_err}")
            return {"error": "Connection Error: Could not connect to Printify API."}
        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Timeout error for {endpoint}: {timeout_err}")
            return {"error": "Timeout Error: Printify API took too long to respond."}
        except requests.exceptions.RequestException as req_err:
            logger.error(f"General Request error for {endpoint}: {req_err}")
            return {"error": f"Request Error: {req_err}"}
        except json.JSONDecodeError as json_err:
            logger.error(f"JSON Decode error for {endpoint}: {json_err} - Response: {response.text}")
            return {"error": f"JSON Decode Error: Invalid response from Printify."}
        except Exception as e:
            logger.exception(f"An unexpected error occurred for {endpoint}:")
            return {"error": f"An unexpected error occurred: {str(e)}"}

    def get_shops(self):
        """
        Fetches the list of shops associated with your Printify account.
        """
        logger.info("🛍️ Fetching shops...")
        return self._make_request('GET', 'shops.json')

    def get_products(self, shop_id, limit=100, page=1):
        """
        Fetches products for a specific shop.
        """
        if not shop_id:
            logger.error("❌ Shop ID is required to fetch products.")
            return {"error": "Shop ID is required."}
        logger.info(f"📦 Fetching products for shop ID: {shop_id}, page: {page}, limit: {limit}")
        return self._make_request('GET', f"shops/{shop_id}/products.json", params={'limit': limit, 'page': page})

    def get_product_details(self, shop_id, product_id):
        """
        Fetches details for a single product.
        """
        if not shop_id or not product_id:
            logger.error("❌ Shop ID and Product ID are required to fetch product details.")
            return {"error": "Shop ID and Product ID are required."}
        logger.info(f"🔍 Fetching details for product {product_id} in shop {shop_id}")
        return self._make_request('GET', f"shops/{shop_id}/products/{product_id}.json")

    def upload_image(self, file_name, contents_base64):
        """
        Uploads an image to Printify's asset library.
        contents_base64 should be the pure base64 string (without "data:image/png;base64,")
        """
        if not file_name or not contents_base64:
            logger.error("❌ File name and base64 content are required for image upload.")
            return {"error": "File name and base64 content are required."}

        # Printify expects the base64 string without the "data:image/png;base64," prefix.
        # Ensure the string is clean before sending.
        # The request in views.py already handles splitting this, so just ensure it's not double-prefixed.
        if contents_base64.startswith("data:"):
            logger.warning("Base64 string for Printify upload still contains 'data:' prefix. Attempting to strip.")
            contents_base64 = contents_base64.split(';base64,')[-1]

        payload = {
            "file_name": file_name,
            "contents": contents_base64
        }
        logger.info(f"⬆️ Attempting to upload image: {file_name} to Printify Assets.")
        return self._make_request('POST', 'uploads/images.json', json_data=payload, timeout=60) # Increased timeout for uploads

    def create_order(self, shop_id, order_payload):
        """
        Creates an order in a Printify shop.
        """
        if not shop_id or not order_payload:
            logger.error("❌ Shop ID and order payload are required to create an order.")
            return {"error": "Shop ID and order payload are required."}
        logger.info(f"🛒 Creating Printify order for shop {shop_id}.")
        return self._make_request('POST', f"shops/{shop_id}/orders.json", json_data=order_payload)

# --- Main execution for testing (optional) ---
if __name__ == "__main__":
    print("🚀 Starting Printify API Script (Standalone Test)...")
    
    # Initialize the client. It will automatically pick up API_TOKEN from .env
    try:
        api_client = PrintifyAPI()
    except ValueError as e:
        print(f"Initialization failed: {e}")
        print("Please ensure PRINTIFY_API_TOKEN is set in your .env file.")
        exit()

    shops_data = api_client.get_shops()

    if shops_data and not shops_data.get('error'):
        first_shop_id = shops_data[0].get('id') if shops_data else None
        if first_shop_id:
            print(f"\nFound shop: {shops_data[0].get('title')} (ID: {first_shop_id})")
            
            # Example: Fetch products from this shop
            products_response = api_client.get_products(first_shop_id)
            if products_response and not products_response.get('error'):
                products_list = products_response.get('data', [])
                print(f"✅ Successfully retrieved {len(products_list)} products from shop ID {first_shop_id}.")
                if products_list:
                    print("\nFirst product details:")
                    print(json.dumps(products_list[0], indent=2))
                else:
                    print("No products found in this shop.")
            else:
                print(f"ℹ️ Could not fetch products: {products_response.get('error', 'Unknown error')}")

            # Example: Get details for a specific product (replace with a real product ID from your shop)
            # if products_list:
            #     sample_product_id = products_list[0].get('id')
            #     product_details_response = api_client.get_product_details(first_shop_id, sample_product_id)
            #     if product_details_response and not product_details_response.get('error'):
            #         print(f"\nDetails for product {sample_product_id}:")
            #         print(json.dumps(product_details_response, indent=2))
            #     else:
            #         print(f"Could not get product details: {product_details_response.get('error', 'Unknown error')}")

            # Example: Simulate an image upload (you'd replace with actual base64 image data)
            # Note: This requires a valid base64 image string. This is just a placeholder.
            # dummy_base64_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
            # upload_res = api_client.upload_image("test_image.png", dummy_base64_image)
            # if upload_res and not upload_res.get('error'):
            #     print(f"\nImage upload successful: {upload_res.get('id')}")
            # else:
            #     print(f"\nImage upload failed: {upload_res.get('error', 'Unknown error')}")

        else:
            print("❌ No shop ID found to proceed with product fetching.")
    else:
        print(f"ℹ️ No shops retrieved: {shops_data.get('error', 'Unknown error')}")

    print("\n🏁 Script finished.")