import os.path
import time
import wget
import webbrowser
import requests
import json

from .UKD import UKDStock as UKD

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

url = 'https://sowerbys.myshopify.com/admin/api/2024-01/graphql.json'
headers = {"Content-Type": "application/graphql",
           "X-Shopify-Access-Token": "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"}
UKDLocationID = "gid://shopify/Location/61867622466"
ShopLocationID = "gid://shopify/Location/17633640514"


class ShopifyResources:

    def __init__(self):
        self.Url = 'https://sowerbys.myshopify.com/admin/api/2023-07/graphql.json'
        self.Headers = {"Content-Type": "application/graphql",
                        "X-Shopify-Access-Token": "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"}
        self.UKD_LocationID = "gid://shopify/Location/61867622466"
        self.ShopLocationID = "gid://shopify/Location/17633640514"
        self.OnlineStorePublicationID = "gid://shopify/Publication/26015563842"
        self.PercentageComplete = 0
        self.Products = []

    def GetLatestShopifyProducts(self):
        CreateBulkQuery = '''mutation {
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

        Received = False
        while not Received:
            try:
                Request = requests.post(self.Url, data=CreateBulkQuery, headers=self.Headers, verify=False)
                Json = json.loads(Request.text)
                OperationID = Json['data']['bulkOperationRunQuery']['bulkOperation']['id']

                Received = True
            except Exception as Error:
                print("*** Error occurred.", Error)

        FetchURLQuery = '''query {
                          node(id: "%s") {
                            ... on BulkOperation {
                                id
                                status
                                errorCode
                                createdAt
                                completedAt
                                objectCount
                                url
                            }
                          }
                        }''' % (OperationID)

        time.sleep(75)
        Received = False
        while not Received:
            try:
                Request = requests.post(self.Url, data=FetchURLQuery, headers=self.Headers, verify=False)
                Json = json.loads(Request.text)
                URL = Json['data']['node']['url']
                print('URL:', URL)
                Received = True
            except Exception as Error:
                print("*** Error occurred.", Error)

        if os.path.exists(os.path.join("files/ShopifyStock.jsonl")):  # if stock file already downloaded and in directory
            os.remove(os.path.join("files/ShopifyStock.jsonl"))  # remove file from directory
        wget.download(URL, os.path.join("files/ShopifyStock.jsonl"))

        self.ProcessJsonl()

    def ProcessJsonl(self):
        with open('files/ShopifyStock.jsonl') as JSN:
            JSONL = [json.loads(Line) for Line in JSN.read().splitlines()]

        self.Products = []
        for Line in JSONL:
            if "'id': 'gid://shopify/Product/" in str(Line):
                pass
            else:
                SKU = Line['sku']
                InventoryID = Line['inventoryItem']['id']
                self.Products.append((SKU, InventoryID))

    def FetchTotalInventoryLevel(self, SKU):
        StockQuery = '''query GetInventoryLevel {
                          productVariants(first: 1, query: "%s") {
                            edges {
                              node {
                              price
                                inventoryItem {
                                            inventoryLevels (first:5) {
                                    edges {
                                      node {
                                        location {
                                          name
                                        }
                                        quantities (names: ["on_hand"]) {
                                          quantity
                                        }
                                      }
                                    }
                                  }
                                    
                                }
                              }
                            }
                          }
                        }''' % (SKU)

        Received = False
        while not Received:
            try:
                Request = requests.post(self.Url, data=StockQuery,
                                        headers=self.Headers, verify=False)  # sends GraphQL to Shopify API and stores response
                Json = json.loads(Request.text)  # transforms returned JSON data into a Python Dict
                print(Json)
                Response = Json['data']['productVariants']['edges']  # stips useless headers from returned JSON data
                Received = True
            except Exception as Error:
                print("** Error occured.", Error)

        if Response != []:  # no match found by Shopify API in DB
            Strings = []
            Price = Response[0]['node']['price']
            for Locations in Response[0]['node']['inventoryItem']['inventoryLevels']['edges']:
                Location = Locations['node']['location']['name']
                Quantity = Locations['node']['quantities'][0]['quantity']
                Strings.append(f"{Quantity} {SKU} in stock at {Location} for £{Price}.")
            return Strings
        return [f'{SKU} does not appear to be stocked by either UKD or Sowerbys Shoes.']

    def FetchCurrentInventoryLevel(self, SKU, LocationID):
        StockQuery = '''query GetInventoryLevel {
                          productVariants(first: 1, query: "%s") {
                            edges {
                              node {
                                inventoryItem {
                                  inventoryLevel (locationId:"%s"){
                                    quantities (names:["on_hand"]) {
                                      quantity
                                    }
                                  }
                                }
                              }
                            }
                          }
                        }''' % (SKU, LocationID)

        Received = False
        while not Received:
            try:
                Request = requests.post(self.Url, data=StockQuery,
                                        headers=self.Headers, verify=False)  # sends GraphQL to Shopify API and stores response
                Json = json.loads(Request.text)  # transforms returned JSON data into a Python Dict
                Response = Json['data']['productVariants']['edges']  # stips useless headers from returned JSON data
                Received = True
            except Exception as Error:
                print("** Error occured.", Error)
        if Response != []:  # no match found by Shopify API in DB
            return Response[0]['node']['inventoryItem']['inventoryLevel']['quantities'][0]['quantity']
        return None

    def GetInventoryID(self, SKU):
        # Method returns shopify inventoryid relevant to the SKU
        SKUQuery = '''query FirstTwentyOneProducts{
                      productVariants (first:1, query:"sku:%s") {
                        edges {
                          node {
                            inventoryItem {
                                id}
                          }
                        }
                      }
                    }''' % (SKU)
        Received = False
        while not Received:
            try:
                Request = requests.post(self.Url, data=SKUQuery, headers=self.Headers, verify=False)
                Json = json.loads(Request.text)
                Response = Json['data']['productVariants']['edges']
                Received = True
            except Exception as Error:
                print("*** Error occured.", Error)

        if Response != []:
            print(f'{SKU} found to be stocked.')
            inventoryID = Response[0]['node']['inventoryItem']['id']
            return inventoryID
        else:
            print(f'{SKU} not found to be stocked.')
            return None

    def CountUpdate(self, Count, Increment):
        if Count % Increment == 0:
            print(f"{Count} products searched")

    def TimeBreak(self, Count, Interval):
        if Count % Interval == 0:
            time.sleep(60)

    def UKDStockUpdate(self):
        UKDStock = UKD().GetFullStock()
        self.GetLatestShopifyProducts()
        NumberOfProducts = len(self.Products)

        while len(self.Products) > 0:
            SKU, InventoryID = self.Products.pop()
            if SKU in UKDStock:
                print(f"{SKU} stocked by UKD.")
                Count = NumberOfProducts - len(self.Products)
                self.CountUpdate(Count, 250)
                self.TimeBreak(Count, 1000)
                self.SetPercentageComplete(Count, NumberOfProducts)

                Quantity = UKDStock[SKU]
                if InventoryID is not None:
                    self.ShopifyStock(InventoryID, self.UKD_LocationID, Quantity)
            else:
                print(f"{SKU} not stocked by UKD.")

    def ShopifyStock(self, InventoryID, LocationID, Quantity):
        update_query = '''mutation {
                  inventorySetOnHandQuantities(input: {
                    # The reason for adjusting the on-hand inventory quantity.
                    reason: "correction",
                    # A freeform URI that represents why the inventory change happened. This can be the entity adjusting inventory quantities or the Shopify resource that's associated with the inventory adjustment. For example, a unit in a draft order might have been previously reserved, and a merchant later creates an order from the draft order. In this case, the referenceDocumentUri for the order ID.
                    referenceDocumentUri: "gid://shopify/Order/1974482927638",
                    # The input that's required to set the on-hand inventory quantity.
                    setQuantities: [
                      {
                        # The ID of the inventory item.
                        inventoryItemId: "%s",
                        # The ID of the location where the inventory is stocked.
                        locationId: "%s",
                        # The quantity of on-hand inventory to set.
                        quantity: %s
                      }
                    ]
                  }
                  ) {
                    inventoryAdjustmentGroup {
                      id
                      changes {
                        name
                        delta
                        quantityAfterChange
                      }
                      reason
                      referenceDocumentUri
                    },
                    userErrors {
                      message
                      code
                      field
                    }
                  }
                }''' % (InventoryID, LocationID, Quantity)
        Received = False
        while not Received:
            try:
                Update = requests.post(url, data=update_query, headers=headers, verify=False)
                Received = True
            except Exception as Error:
                print("**** Error occured.", Error)

    def ChangeStock(self, SKU, Location, Change):
        InventoryID = self.GetInventoryID(SKU)
        NewInventoryLevel = self.FetchCurrentInventoryLevel(SKU, Location) + Change
        self.ShopifyStock(InventoryID, Location, NewInventoryLevel)

    def SetStock(self, SKU, Location, Quantiy):
        InventoryID = self.GetInventoryID(SKU)
        self.ShopifyStock(InventoryID, Location, Quantiy)

    def SetPercentageComplete(self, Searched, Total):
        self.PercentageComplete = round((Searched / Total) * 100)

    def GetProductByStyleNo(self, style_no):
        """Search for a product in Shopify using StyleNo"""
        # Remove any spaces from the style_no
        style_no = style_no.replace(' ', '')
        
        query = '''
        query getVariantDetails {
          productVariants(first: 1, query: "sku:%s*") {
            edges {
              node {
                price
                image {
                  originalSrc
                }
                product {
                  title
                }
              }
            }
          }
        }
        ''' % (style_no)

        print(f"Searching Shopify for StyleNo: {style_no}")
        
        try:
            response = requests.post(self.Url, data=query, headers=self.Headers, verify=False)
            json_response = json.loads(response.text)
            
            if 'data' in json_response and json_response['data']['productVariants']['edges']:
                variant = json_response['data']['productVariants']['edges'][0]['node']
                product = variant['product']
                
                # Extract the relevant information
                result = {
                    'title': product['title'],
                    'price': variant['price'],
                    'image_url': variant['image']['originalSrc'] if variant['image'] else None,
                    'found': True
                }
                print(f"Found Shopify product: {result}")
                return result
            else:
                print(f"No Shopify product found for StyleNo: {style_no}")
                return {'found': False}
                
        except Exception as e:
            print(f"Error searching Shopify: {str(e)}")
            return {'found': False, 'error': str(e)} 