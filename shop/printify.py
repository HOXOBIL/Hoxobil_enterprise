import os
import requests
from dotenv import load_dotenv
import json # Added for potentially pretty-printing the JSON response

# Load environment variables from .env file
load_dotenv()

# Get the Printify API token from the .env file
PRINTIFY_API_TOKEN = os.getenv('PRINTIFY_API_TOKEN')

# Ensure token is loaded
if not PRINTIFY_API_TOKEN:
    raise ValueError("PRINTIFY_API_TOKEN is not set in the .env file. Please ensure it's defined.")

# Set up headers for authentication
# This is the corrected part: using the PRINTIFY_API_TOKEN variable
HEADERS = {
    'Authorization': f'Bearer {PRINTIFY_API_TOKEN}',
    'Content-Type': 'application/json' # Good practice to include Content-Type
}

def get_shop_id():
    """
    Fetch the list of shops associated with your Printify account.
    Returns:
        list: A list of shop dictionaries, or an empty list if an error occurs.
    """
    url = "https://api.printify.com/v1/shops.json"
    print("🛍️ Fetching shops...")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10) # Added timeout
        response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)

        print(f"✅ Shops API Status Code: {response.status_code}")
        data = response.json()
        print("✅ Shops retrieved successfully.")
        if not data:
            print("ℹ️ No shops found for this account.")
            return []
        for shop in data:
            print(f"🛒 Shop: {shop.get('title')} (ID: {shop.get('id')})")
        return data
    except requests.exceptions.HTTPError as http_err:
        print(f"❌ HTTP error fetching shops: {http_err} - Response: {response.text}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"❌ Connection error fetching shops: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"❌ Timeout error fetching shops: {timeout_err}")
    except requests.exceptions.RequestException as req_err: # Catching broader request exceptions
        print(f"❌ Error fetching shops: {req_err}")
    except json.JSONDecodeError as json_err:
        print(f"❌ Error parsing shop JSON: {json_err} - Response was: {response.text}")
    return []


def get_products(shop_id):
    """
    Fetch all products for a specific shop.

    Args:
        shop_id (int or str): The ID of the shop.
    Returns:
        list: A list of product dictionaries, or an empty list if an error occurs.
    """
    if not shop_id:
        print("❌ Shop ID is required to fetch products.")
        return []

    url = f"https://api.printify.com/v1/shops/{shop_id}/products.json"
    print(f"\n📦 Fetching products for shop ID: {shop_id}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=15) # Added timeout
        response.raise_for_status() # Raises an HTTPError for bad responses

        print(f"✅ Products API Status Code: {response.status_code}")
        # The API returns a dictionary with a 'data' key containing the list of products
        response_data = response.json()
        products = response_data.get('data', []) # Access the list of products under the 'data' key

        print(f"✅ Found {len(products)} products.")
        if products:
            sample = products[0] # Get the first product for sample output
            print("\n🔍 Sample product details:")
            print(f"  ID: {sample.get('id')}")
            print(f"  Title: {sample.get('title')}")

            # Images: A product has a list of images. We'll take the first one.
            images = sample.get('images', [])
            if images:
                # Prioritize 'src' for the main image URL
                # Images can have different properties like 'is_default', 'is_selected_for_publishing'
                # You might want to add logic to pick a specific image.
                # For simplicity, taking the first image's 'src'.
                first_image_url = images[0].get('src')
                print(f"  Image URL: {first_image_url}")
            else:
                print("  Image URL: Not available")

            # Variants: A product has variants (e.g., size, color), each with its own price.
            variants = sample.get('variants', [])
            if variants:
                first_variant = variants[0]
                # Price is in cents (or smallest currency unit).
                # For NGN (Naira), if Printify stores it in kobo, 100 kobo = 1 Naira.
                # Adjust the divisor if Printify uses a different smallest unit for NGN.
                price_in_smallest_unit = first_variant.get('price')
                if price_in_smallest_unit is not None:
                    # Assuming price is in kobo for NGN, convert to Naira
                    price_in_naira = price_in_smallest_unit / 100
                    print(f"  Price (first variant): ₦{price_in_naira:.2f} (Raw: {price_in_smallest_unit})")
                else:
                    print("  Price (first variant): Not available")

                print(f"  SKU (first variant): {first_variant.get('sku')}")
                print(f"  Stock (first variant): {'In stock' if first_variant.get('is_available') else 'Out of stock'}")
            else:
                print("  Variants: Not available")

            # Uncomment to print the full sample product data for debugging
            # print("\n📋 Full sample product data:")
            # print(json.dumps(sample, indent=2))

        return products
    except requests.exceptions.HTTPError as http_err:
        print(f"❌ HTTP error fetching products: {http_err} - Response: {response.text}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"❌ Connection error fetching products: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"❌ Timeout error fetching products: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"❌ Error fetching products: {req_err}")
    except json.JSONDecodeError as json_err: # More specific JSON error
        print(f"❌ Error parsing products JSON: {json_err} - Response was: {response.text}")
    return []

# --- Main execution ---
if __name__ == "__main__":
    print("🚀 Starting Printify API Script...")

    if not PRINTIFY_API_TOKEN:
        print("🚫 PRINTIFY_API_TOKEN is missing. Script cannot proceed.")
    else:
        shops_data = get_shop_id()

        if shops_data:
            # Example: Get products from the first shop found
            # You might want to let the user select a shop or use a specific shop ID
            first_shop_id = shops_data[0].get('id')
            if first_shop_id:
                products_data = get_products(first_shop_id)
                # You can now do something with products_data,
                # e.g., pass it to your Django backend or process it further.
                if products_data:
                    print(f"\n✅ Successfully retrieved {len(products_data)} products from shop ID {first_shop_id}.")
                    # print(json.dumps(products_data, indent=2)) # Optional: print all products
                else:
                    print(f"ℹ️ No products found or an error occurred for shop ID {first_shop_id}.")
            else:
                print("❌ Could not determine the ID of the first shop.")
        else:
            print("ℹ️ No shops retrieved, cannot fetch products.")

    print("\n🏁 Script finished.")
