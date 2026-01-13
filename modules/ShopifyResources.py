import os.path
import os
import time
import wget
import webbrowser
import requests
import json
import urllib3
import pandas as pd

from .UKD import UKDStock as UKD

import ssl

ssl._create_default_https_context = ssl._create_unverified_context

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ShopifyResources:

    def __init__(self):
        self.Url = os.getenv("API-Url")
        self.Headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": os.getenv("X-Shopify-Access-Token"),
        }
        self.UKD_LocationID = f"gid://shopify/Location/{os.getenv('UKDLocationID')}"
        self.ShopLocationID = f"gid://shopify/Location/{os.getenv('ShopLocationID')}"
        self.OnlineStorePublicationID = (
            f"gid://shopify/Publication/{os.getenv('OnlineStorePublicationID')}"
        )
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

        # Start the bulk operation, retrying on errors and logging responses
        Received = False
        retry_count = 0
        max_retries = 10
        while not Received and retry_count < max_retries:
            try:
                Request = requests.post(
                    self.Url,
                    data=json.dumps({"query": CreateBulkQuery}),
                    headers=self.Headers,
                )
                if Request.status_code != 200:
                    print(
                        f"*** Error: bulkOperationRunQuery HTTP {Request.status_code}: {Request.text}"
                    )
                    retry_count += 1
                    time.sleep(10)
                    continue
                Json = Request.json()
                if "errors" in Json:
                    print(f"*** GraphQL errors: {Json['errors']}")
                    retry_count += 1
                    time.sleep(10)
                    continue
                # Safely extract OperationID
                data = Json.get("data", {})
                bulkOp = data.get("bulkOperationRunQuery", {})
                op = bulkOp.get("bulkOperation", {})
                OperationID = op.get("id")
                if not OperationID:
                    print(f"*** No OperationID in response; full payload: {Json}")
                    retry_count += 1
                    time.sleep(10)
                    continue
                print(f"Started bulkOperation with ID: {OperationID}")
                Received = True
            except Exception as Error:
                print("*** Exception during bulkOperationRunQuery:", Error)
                retry_count += 1
                time.sleep(10)
        if not Received:
            print("*** Failed to start bulk operation after maximum retries.")
            return

        FetchURLQuery = """query {
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
                        }""" % (
            OperationID
        )

        # Poll for completion status, up to a max number of retries
        retry_count = 0
        max_retries = 30
        URL = None
        while retry_count < max_retries:
            try:
                resp = requests.post(
                    self.Url,
                    data=json.dumps({"query": FetchURLQuery}),
                    headers=self.Headers,
                )
                if resp.status_code != 200:
                    print(f"*** Error: FetchURLQuery HTTP {resp.status_code}")
                else:
                    Json = resp.json()
                    if "errors" in Json:
                        print("*** GraphQL errors:", Json["errors"])
                    else:
                        node = Json.get("data", {}).get("node", {})
                        status = node.get("status")
                        print(f"Bulk operation status: {status}")
                        if status == "COMPLETED":
                            URL = node.get("url")
                            break
                retry_count += 1
                time.sleep(10)
            except Exception as Error:
                print("*** Exception during FetchURLQuery:", Error)
                retry_count += 1
                time.sleep(10)
        if not URL:
            print(
                f"*** Bulk operation did not complete in time after {max_retries} retries."
            )
            return

        if os.path.exists(
            os.path.join("files/ShopifyStock.jsonl")
        ):  # if stock file already downloaded and in directory
            os.remove(
                os.path.join("files/ShopifyStock.jsonl")
            )  # remove file from directory
        print(f"Starting download of JSONL from {URL}")
        wget.download(URL, os.path.join("files/ShopifyStock.jsonl"))
        print("Download complete.")

        self.ProcessJsonl()

    def ProcessJsonl(self):
        with open("files/ShopifyStock.jsonl") as JSN:
            JSONL = [json.loads(Line) for Line in JSN.read().splitlines()]

        self.Products = []
        for Line in JSONL:
            if "'id': 'gid://shopify/Product/" in str(Line):
                pass
            else:
                SKU = Line["sku"]
                InventoryID = Line["inventoryItem"]["id"]
                self.Products.append((SKU, InventoryID))

    def FetchTotalInventoryLevel(self, SKU):
        StockQuery = """query GetInventoryLevel {
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
                        }""" % (
            SKU
        )

        Received = False
        while not Received:
            try:
                Request = requests.post(
                    self.Url, data=StockQuery, headers=self.Headers, verify=False
                )  # sends GraphQL to Shopify API and stores response
                Json = json.loads(
                    Request.text
                )  # transforms returned JSON data into a Python Dict
                print(Json)
                Response = Json["data"]["productVariants"][
                    "edges"
                ]  # stips useless headers from returned JSON data
                Received = True
            except Exception as Error:
                print("** Error occured.", Error)

        if Response != []:  # no match found by Shopify API in DB
            Strings = []
            Price = Response[0]["node"]["price"]
            for Locations in Response[0]["node"]["inventoryItem"]["inventoryLevels"][
                "edges"
            ]:
                Location = Locations["node"]["location"]["name"]
                Quantity = Locations["node"]["quantities"][0]["quantity"]
                Strings.append(f"{Quantity} {SKU} in stock at {Location} for £{Price}.")
            return Strings
        return [f"{SKU} does not appear to be stocked by either UKD or Sowerbys Shoes."]

    def FetchCurrentInventoryLevel(self, SKU, LocationID):
        StockQuery = """query GetInventoryLevel {
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
                        }""" % (
            SKU,
            LocationID,
        )

        Received = False
        while not Received:
            try:
                Request = requests.post(
                    self.Url, data=StockQuery, headers=self.Headers, verify=False
                )  # sends GraphQL to Shopify API and stores response
                Json = json.loads(
                    Request.text
                )  # transforms returned JSON data into a Python Dict
                Response = Json["data"]["productVariants"][
                    "edges"
                ]  # stips useless headers from returned JSON data
                Received = True
            except Exception as Error:
                print("** Error occured.", Error)
        if Response != []:  # no match found by Shopify API in DB
            return Response[0]["node"]["inventoryItem"]["inventoryLevel"]["quantities"][
                0
            ]["quantity"]
        return None

    def GetInventoryID(self, SKU):
        # Method returns shopify inventoryid relevant to the SKU
        SKUQuery = """query FirstTwentyOneProducts{
                      productVariants (first:1, query:"sku:%s") {
                        edges {
                          node {
                            inventoryItem {
                                id}
                          }
                        }
                      }
                    }""" % (
            SKU
        )
        Received = False
        while not Received:
            try:
                Request = requests.post(
                    self.Url, data=SKUQuery, headers=self.Headers, verify=False
                )
                Json = json.loads(Request.text)
                Response = Json["data"]["productVariants"]["edges"]
                Received = True
            except Exception as Error:
                print("*** Error occured.", Error)

        if Response != []:
            print(f"{SKU} found to be stocked.")
            inventoryID = Response[0]["node"]["inventoryItem"]["id"]
            return inventoryID
        else:
            print(f"{SKU} not found to be stocked.")
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
        update_query = """mutation {
                  inventorySetOnHandQuantities(input: {
                    reason: "correction",
                    referenceDocumentUri: "gid://shopify/Order/1974482927638",
                    setQuantities: [
                      {
                        inventoryItemId: "%s",
                        locationId: "%s",
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
                    }
                    userErrors {
                      message
                      code
                      field
                    }
                  }
                }""" % (
            InventoryID,
            LocationID,
            Quantity,
        )

        Received = False
        while not Received:
            try:
                payload = {"query": update_query}
                Update = requests.post(self.Url, headers=self.Headers, json=payload)
                result = Update.json()
                Received = True
            except Exception as Error:
                print("**** Error occurred in ShopifyStock:", Error)

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
        style_no = style_no.replace(" ", "")

        query = """
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
        """ % (
            style_no
        )

        print(f"Searching Shopify for StyleNo: {style_no}")

        try:
            response = requests.post(
                self.Url, data=query, headers=self.Headers, verify=False
            )
            json_response = json.loads(response.text)

            if (
                "data" in json_response
                and json_response["data"]["productVariants"]["edges"]
            ):
                variant = json_response["data"]["productVariants"]["edges"][0]["node"]
                product = variant["product"]

                # Extract the relevant information
                result = {
                    "title": product["title"],
                    "price": variant["price"],
                    "image_url": (
                        variant["image"]["originalSrc"] if variant["image"] else None
                    ),
                    "found": True,
                }
                print(f"Found Shopify product: {result}")
                return result
            else:
                print(f"No Shopify product found for StyleNo: {style_no}")
                return {"found": False}

        except Exception as e:
            print(f"Error searching Shopify: {str(e)}")
            return {"found": False, "error": str(e)}

    def get_all_publication_ids(self):
        """Fetch all publication IDs (sales channels) from Shopify."""
        query = """{\n  publications(first: 20) {\n    edges {\n      node {\n        id\n        name\n      }\n    }\n  }\n}"""
        try:
            response = requests.post(
                self.Url, data=query, headers=self.Headers, verify=False
            )
            result = response.json()
            if "data" in result and "publications" in result["data"]:
                publications = result["data"]["publications"]["edges"]
                return [
                    (pub["node"]["id"], pub["node"]["name"]) for pub in publications
                ]
            else:
                print("Could not fetch publications:", result)
                return []
        except Exception as e:
            print(f"Error fetching publications: {e}")
            return []

    def AddProducts(
        self, Title, Description, Options, Variants, Images, Vendor, AllImages
    ):
        """Add a new product to Shopify with variants and publish to all sales channels (manually encoded)."""
        # Escape quotes in strings to prevent JSON syntax errors
        Title = Title.replace('"', '\\"')
        Description = Description.replace('"', '\\"')
        # Capitalize each word in vendor
        Vendor = Vendor.title().replace('"', '\\"')

        # Better debugging for image issues
        print("\n=== DEBUGGING IMAGES PARAMETER ===")
        print(f"Images parameter type: {type(Images)}")
        print(f"Images parameter value: {Images}")
        print(
            f"Images parameter length: {len(Images) if isinstance(Images, str) else 'N/A'}"
        )

        # Force proper format if Images is empty or malformed
        if not Images or Images == "[]" or "mediaContentType" not in Images:
            print(
                "Warning: No valid images provided for product or images parameter is empty"
            )
            # If we need to add a test image for debugging:
            # Images = '''[{mediaContentType:IMAGE,originalSource:"https://example.com/test.jpg"}]'''

        mutation = f"""mutation productCreate {{
          productCreate(input: {{
            title: "{Title}",
            descriptionHtml: "{Description}",
            vendor: "{Vendor}",
          }}, media: {Images}) {{
            product {{
              id
              media(first:50) {{
                edges {{
                  node {{
                    ... on MediaImage {{
                      id
                    }}
                  }}
                }}
              }}
            }}
            userErrors {{
              field
              message
            }}
          }}
        }}"""

        print("\nFull mutation:")
        print(mutation)
        print("=== End Mutation ===\n")

        try:
            payload = {"query": mutation}
            response = requests.post(self.Url, headers=self.Headers, json=payload)
            result = response.json()

            print("\n=== API Response ===")
            print(json.dumps(result, indent=2))
            print("=== End Response ===\n")

            product_id = result["data"]["productCreate"]["product"]["id"]

        except Exception as e:
            print("Error in AddProducts:", str(e))
            return None

        nodes = result["data"]["productCreate"]["product"]["media"]["edges"]
        images = []
        for node in nodes:
            images.append(node["node"]["id"])

        mappings = dict(zip(AllImages, images))

        add_options_mutation = f"""mutation {{
          productOptionsCreate(
            productId: "{product_id}",
            options: {Options}
            variantStrategy: CREATE
          ) {{
            product {{
                id
                variants(first:50) {{
                    edges {{
                        node {{
                            id
                            selectedOptions {{
                              name
                              value
                            }}
                            inventoryItem {{
                              id
                            }}
                        }}
                    }}
                }}
            }}
            userErrors {{
              field
              message
              code
            }}
          }}
        }}"""

        print("\nFull add_options_mutation:")
        print(add_options_mutation)
        print("=== End add_options_mutation ===\n")

        try:
            payload = {"query": add_options_mutation}
            response = requests.post(self.Url, headers=self.Headers, json=payload)
            result = response.json()
            print(result)

        except Exception as e:
            print("Error in AddOptions:", str(e))
            return None

        # Extract edges
        print("before extraction")
        edges = result["data"]["productOptionsCreate"]["product"]["variants"]["edges"]

        # Build list of dicts and extract inventoryItem IDs for ShopifyStock calls
        records = []
        inventory_items = []  # Store inventoryItem data for stock updates

        for edge in edges:
            node = edge["node"]
            variant_id = node["id"]
            inventory_item_id = node["inventoryItem"]["id"]
            options = {
                opt["name"].lower(): opt["value"] for opt in node["selectedOptions"]
            }

            records.append(
                {
                    "id": variant_id,
                    "color": options.get("color"),
                    "size": options.get("size"),
                }
            )

            # Store inventory item data for later stock updates
            inventory_items.append(
                {
                    "inventoryItemId": inventory_item_id,
                    "color": options.get("color"),
                    "size": options.get("size"),
                }
            )

        # Convert to DataFrame
        df = pd.DataFrame(records)
        print("after extraction")

        def build_bulk_update_query(
            product_id: str, df: pd.DataFrame, variants_data: list
        ) -> str:
            """
            Build a Shopify bulk variant update GraphQL mutation.

            Args:
                product_id (str): Shopify product GID.
                df (pd.DataFrame): DataFrame with columns ['color', 'size', 'id'].
                variants_data (list): List of dicts with keys matching Shopify variant fields.

            Returns:
                str: GraphQL mutation string.
            """
            print(type(variants_data))
            print(variants_data)
            variant_blocks = []
            print("inside function")

            for v in variants_data:  # v is already a dict
                color = next(
                    o["name"] for o in v["optionValues"] if o["optionName"] == "Color"
                )
                size = next(
                    o["name"] for o in v["optionValues"] if o["optionName"] == "Size"
                )

                # lookup id from DataFrame
                match = df[(df["color"] == color) & (df["size"] == size)]
                if match.empty:
                    print(f"⚠️ No match for {color} {size}, skipping...")
                    continue

                variant_id = match.iloc[0]["id"]

                # Use mappings dict for image lookup instead of AllImages (which may be a set)
                media_id = (
                    mappings.get(v["imageUrl"]) if "mappings" in locals() else None
                )
                if not media_id:
                    print(f"⚠️ No mediaId for imageUrl {v['imageUrl']}, skipping...")
                    continue

                block = f"""
                {{
                  id: "{variant_id}"
                  price: "{v["price"]}"
                  barcode: "{v["barcode"]}"
                  mediaId: "{media_id}"
                  inventoryPolicy: {v["inventoryPolicy"]}
                  inventoryItem: {{
                    tracked: {str(v["inventoryItem"]["tracked"]).lower()}
                    sku: "{v["inventoryItem"]["sku"]}"
                    cost: {v["inventoryItem"]["cost"]}
                  }}
                }}"""
                variant_blocks.append(block)

            print("outside loop")
            variants_str = ",\n".join(variant_blocks)

            print("BUILDING UPDATE QUERY")
            query = f"""
            mutation {{
              productVariantsBulkUpdate(
                productId: "{product_id}"
                variants: [{variants_str}]
              ) {{
                product {{
                  id
                  title
                  variants(first: 20) {{
                    edges {{
                      node {{
                        id
                        sku
                        price
                      }}
                    }}
                  }}
                }}
                userErrors {{
                  field
                  message
                }}
              }}
            }}
            """
            return query

        # Example usage
        query = build_bulk_update_query(product_id, df, Variants)

        print("\nFull add_variants_mutation:")
        print(query)
        print("=== End add_variants_mutation ===\n")
        try:
            payload = {"query": query}
            response = requests.post(self.Url, headers=self.Headers, json=payload)
            result = response.json()
            print(result)

        except Exception as e:
            print("Error in AddVariants:", str(e))
            return None

        # Activate all inventory items at once using bulk toggle activation
        print("Activating all inventory items at UKD location...")
        ukd_location = "gid://shopify/Location/61867622466"  # UKD location ID

        # Collect all inventory item IDs
        inventory_item_ids = [item["inventoryItemId"] for item in inventory_items]

        if inventory_item_ids:
            # Create inventoryBulkToggleActivation mutation using the correct format with variables
            bulk_activate_mutation = """mutation inventoryBulkToggleActivation($inventoryItemId: ID!, $inventoryItemUpdates: [InventoryBulkToggleActivationInput!]!) {
              inventoryBulkToggleActivation(inventoryItemId: $inventoryItemId, inventoryItemUpdates: $inventoryItemUpdates) {
                inventoryItem {
                  id
                }
                inventoryLevels {
                  id
                  quantities(names: ["available"]) {
                    name
                    quantity
                  }
                  location {
                    id
                  }
                }
                userErrors {
                  field
                  message
                  code
                }
              }
            }"""

            print("Bulk activation mutation:")
            print(bulk_activate_mutation)
            print("=== End bulk activation mutation ===\n")

            # Process each inventory item individually since the mutation expects one inventoryItemId at a time
            for inventory_item_id in inventory_item_ids:
                variables = {
                    "inventoryItemId": inventory_item_id,
                    "inventoryItemUpdates": [
                        {"locationId": ukd_location, "activate": True}
                    ],
                }

                print(f"Activating inventory item: {inventory_item_id}")
                print(f"Variables: {variables}")

                try:
                    payload = {"query": bulk_activate_mutation, "variables": variables}
                    response = requests.post(
                        self.Url, headers=self.Headers, json=payload
                    )
                    result = response.json()

                    if "errors" in result:
                        print(
                            f"Error in bulk activation for {inventory_item_id}: {result['errors']}"
                        )
                    else:
                        print(
                            f"Inventory item {inventory_item_id} activated successfully"
                        )
                        if (
                            result.get("data", {})
                            .get("inventoryBulkToggleActivation", {})
                            .get("userErrors")
                        ):
                            print(
                                f"User errors: {result['data']['inventoryBulkToggleActivation']['userErrors']}"
                            )

                except Exception as e:
                    print(
                        f"Error activating inventory item {inventory_item_id}: {str(e)}"
                    )
                    continue

        # Now set individual stock levels using ShopifyStock
        print("Setting individual stock levels...")

        for inventory_item in inventory_items:
            # Find matching variant in Variants data to get stock quantity
            matching_variant = None
            for variant in Variants:
                color = next(
                    (
                        o["name"]
                        for o in variant["optionValues"]
                        if o["optionName"] == "Color"
                    ),
                    None,
                )
                size = next(
                    (
                        o["name"]
                        for o in variant["optionValues"]
                        if o["optionName"] == "Size"
                    ),
                    None,
                )

                if color == inventory_item["color"] and size == inventory_item["size"]:
                    matching_variant = variant
                    break

            if matching_variant and "inventoryQuantities" in matching_variant:
                stock_quantity = matching_variant["inventoryQuantities"][0][
                    "availableQuantity"
                ]
                print(
                    f"Setting stock for {inventory_item['color']} {inventory_item['size']}: {stock_quantity}"
                )

                try:
                    self.ShopifyStock(
                        inventory_item["inventoryItemId"], ukd_location, stock_quantity
                    )
                    print(
                        f"Stock updated successfully for {inventory_item['color']} {inventory_item['size']}"
                    )
                except Exception as e:
                    print(
                        f"Error updating stock for {inventory_item['color']} {inventory_item['size']}: {str(e)}"
                    )
            else:
                print(
                    f"No matching variant found for {inventory_item['color']} {inventory_item['size']}"
                )

        print("Stock update process completed.")
