import requests
import json

# Shopify API URL and access token
shop_url = 'https://sowerbys.myshopify.com/admin/api/2024-01/graphql.json'
access_token = "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"

# GraphQL mutation for product creation with escaped HTML content
mutation = """
mutation productCreate {
  productCreate(input: {
    title: "test",
    descriptionHtml: "<p><strong>ARMA S3 WATERPROOF SAFETY BOOT</strong></p><ul><li>Black leather upper</li><li>Waterproof and breathable membrane</li><li>Metal Free</li><li>Breathable moisture wicking lining for comfort</li><li>Full length removable memory foam insole for comfort</li><li>Durable dual density PU outsole</li><li>Shock absorbing heal</li><li>Heavy duty metal free hardware with speed lace cleats</li><li>Penetration resistant non metallic midsole</li><li>Antistatic</li><li>Padded collar and bellows tongue</li><li>EN ISO 20345:2011 S3 – SRC certified</li></ul><p>Don't forget, we pay the postage! Shipped from our family run store in Stourbridge.</p>",
    options: ["Color", "Size"],
    variants: [
      {
        mediaSrc: "https://global-safety.co.uk/wp-content/uploads/2018/05/A8-SCOUT.png",
        options: ["Black", "6"],
        sku: "a8/06",
        price: 0,
        inventoryItem: {
          tracked: true,
          cost: 2850
        },
        inventoryPolicy: DENY,
        inventoryQuantities: [
          {
            locationId: "gid://shopify/Location/61867622466",
            availableQuantity: 5
          }
        ]
      },
      {
        mediaSrc: "https://global-safety.co.uk/wp-content/uploads/2018/05/A8-SCOUT.png",
        options: ["Black", "7"],
        sku: "a8/07",
        price: 0,
        inventoryItem: {
          tracked: true,
          cost: 2850
        },
        inventoryPolicy: DENY,
        inventoryQuantities: [
          {
            locationId: "gid://shopify/Location/61867622466",
            availableQuantity: 5
          }
        ]
      },
      {
        mediaSrc: "https://global-safety.co.uk/wp-content/uploads/2018/05/A8-SCOUT.png",
        options: ["Black", "8"],
        sku: "a8/08",
        price: 0,
        inventoryItem: {
          tracked: true,
          cost: 2850
        },
        inventoryPolicy: DENY,
        inventoryQuantities: [
          {
            locationId: "gid://shopify/Location/61867622466",
            availableQuantity: 5
          }
        ]
      },
      {
        mediaSrc: "https://global-safety.co.uk/wp-content/uploads/2018/05/A8-SCOUT.png",
        options: ["Black", "9"],
        sku: "a8/09",
        price: 0,
        inventoryItem: {
          tracked: true,
          cost: 2850
        },
        inventoryPolicy: DENY,
        inventoryQuantities: [
          {
            locationId: "gid://shopify/Location/61867622466",
            availableQuantity: 5
          }
        ]
      },
      {
        mediaSrc: "https://global-safety.co.uk/wp-content/uploads/2018/05/A8-SCOUT.png",
        options: ["Black", "10"],
        sku: "a8/10",
        price: 0,
        inventoryItem: {
          tracked: true,
          cost: 2850
        },
        inventoryPolicy: DENY,
        inventoryQuantities: [
          {
            locationId: "gid://shopify/Location/61867622466",
            availableQuantity: 5
          }
        ]
      },
      {
        mediaSrc: "https://global-safety.co.uk/wp-content/uploads/2018/05/A8-SCOUT.png",
        options: ["Black", "11"],
        sku: "a8/11",
        price: 0,
        inventoryItem: {
          tracked: true,
          cost: 2850
        },
        inventoryPolicy: DENY,
        inventoryQuantities: [
          {
            locationId: "gid://shopify/Location/61867622466",
            availableQuantity: 5
          }
        ]
      },
      {
        mediaSrc: "https://global-safety.co.uk/wp-content/uploads/2018/05/A8-SCOUT.png",
        options: ["Black", "12"],
        sku: "a8/12",
        price: 0,
        inventoryItem: {
          tracked: true,
          cost: 2850
        },
        inventoryPolicy: DENY,
        inventoryQuantities: [
          {
            locationId: "gid://shopify/Location/61867622466",
            availableQuantity: 5
          }
        ]
      },
      {
        mediaSrc: "https://global-safety.co.uk/wp-content/uploads/2018/05/A8-SCOUT.png",
        options: ["Black", "13"],
        sku: "a8/13",
        price: 0,
        inventoryItem: {
          tracked: true,
          cost: 2850
        },
        inventoryPolicy: DENY,
        inventoryQuantities: [
          {
            locationId: "gid://shopify/Location/61867622466",
            availableQuantity: 5
          }
        ]
      },
      {
        mediaSrc: "https://global-safety.co.uk/wp-content/uploads/2018/05/A8-SCOUT.png",
        options: ["Black", "14"],
        sku: "a8/14",
        price: 0,
        inventoryItem: {
          tracked: true,
          cost: 2850
        },
        inventoryPolicy: DENY,
        inventoryQuantities: [
          {
            locationId: "gid://shopify/Location/61867622466",
            availableQuantity: 5
          }
        ]
      }
    ],
    vendor: "ARMA",
    tags: []
  }, media: [
    {
      mediaContentType: IMAGE,
      originalSource: "https://global-safety.co.uk/wp-content/uploads/2018/05/A8-SCOUT.png"
    },
    {
      mediaContentType: IMAGE,
      originalSource: "https://global-safety.co.uk/wp-content/uploads/2018/05/A8-SCOUT-6.png"
    },
    {
      mediaContentType: IMAGE,
      originalSource: "https://global-safety.co.uk/wp-content/uploads/2018/05/A8-SCOUT-5.png"
    },
    {
      mediaContentType: IMAGE,
      originalSource: "https://global-safety.co.uk/wp-content/uploads/2018/05/A8-SCOUT-4.png"
    },
    {
      mediaContentType: IMAGE,
      originalSource: "https://global-safety.co.uk/wp-content/uploads/2018/05/A8-SCOUT-3.png"
    },
    {
      mediaContentType: IMAGE,
      originalSource: "https://global-safety.co.uk/wp-content/uploads/2018/05/A8-SCOUT-2.png"
    },
    {
      mediaContentType: IMAGE,
      originalSource: "https://global-safety.co.uk/wp-content/uploads/2018/05/A8-SCOUT-1.png"
    }
  ]) {
    product {
      id
      title
    }
  }
}
"""

# Prepare headers
headers = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": access_token
}

# Prepare the payload
payload = json.dumps({"query": mutation})

# Send the request
response = requests.post(shop_url, headers=headers, data=payload)

# Check the response
print(response.json())