

import requests
import json

url = 'https://sowerbys.myshopify.com/admin/api/2025-07/graphql.json'
headers = {
    "Content-Type": "application/json",   # must be application/json
    "X-Shopify-Access-Token": "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"
}

query = """
mutation productCreate {
          productCreate(input: {
            title: "MATILDA",
            descriptionHtml: "<ul><li>Floral Embroidered Textile upper</li><li>V Cut Touch Fastening Slipper</li><li>Vulcanised Rubber Sole sole</li></ul><p>Don't forget, we pay the postage! Shipped from our family run store in Stourbridge.</p>",
            vendor: "Sleepers",
          }, media: [{mediaContentType:IMAGE,originalSource:"http://127.0.0.1:5000/static/cache/products/LS182F.jpg"},{mediaContentType:IMAGE,originalSource:"http://127.0.0.1:5000/static/cache/products/LS182F2.jpg"},{mediaContentType:IMAGE,originalSource:"http://127.0.0.1:5000/static/cache/products/LS182NC.jpg"},{mediaContentType:IMAGE,originalSource:"http://127.0.0.1:5000/static/cache/products/LS182NC2.jpg"}]) {
            product {
              id
              media(first=50) {
                edges {
                  node {
                    ... on MediaImage {
                      id
                    }
                  }
                }
              }
            }
            userErrors {
              field
              message
            }
          }
        }
"""

payload = {"query": query}

response = requests.post(url, headers=headers, json=payload)  # use json= instead of data=
print(response.status_code)
print(response.json())
