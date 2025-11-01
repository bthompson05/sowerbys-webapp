import requests
import json

# === Configuration ===
SHOPIFY_SHOP = "sowerbys.myshopify.com"
ACCESS_TOKEN = "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"  # your private app token

# === GraphQL endpoint ===
url = f"https://{SHOPIFY_SHOP}/admin/api/2025-01/graphql.json"

# === Define the mutation ===
mutation = '''mutation {
                              bulkOperationRunQuery(
                               query: """
                                {
                                  products {
                                    edges {
                                      node {
                                        id
                                        variants(first: 250)
                                    {
                                      edges {
                                        node {
                                          sku
                                          inventoryItem {
                                            id  #this is the inventory_item_id
                                          }
                                        }
                                      }
                                    }
                                      }
                                    }
                                  }
                                }
                                """
                              ) {
                                bulkOperation {
                                  id
                                  status
                                }
                                userErrors {
                                  field
                                  message
                                }
                              }
                            }'''

# === Build variables ===
variables = {
    "query": mutation,
    "groupObjects": False
}

# === Send request ===
headers = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": ACCESS_TOKEN
}

payload = {
    "query": mutation,
    "variables": variables
}

response = requests.post(url, headers=headers, data=json.dumps(payload))

# === Handle response ===
if response.status_code == 200:
    data = response.json()
    print(json.dumps(data, indent=2))
else:
    print(f"Request failed: {response.status_code}")
    print(response.text)
