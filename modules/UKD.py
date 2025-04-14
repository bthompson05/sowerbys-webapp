import csv
import os
import wget
import logging

UKDStockFileLink = 'https://www.ukdistributors.co.uk/downloads/xStockFile2.csv'
UKDDataFileLink = 'https://www.ukdistributors.co.uk/downloads/xStockFile6.csv'
UKDImageLink = 'https://www.ukdistributors.co.uk/photos/840/'

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

class UKDStock:

    def __init__(self):
        # Ensure files directory exists
        os.makedirs("files", exist_ok=True)
        self.__DownloadStock()  # Downloads latest stock each time program loaded
        self.ShopLocationID = "gid://shopify/Location/17633640514"  # Shopify tag for shop location
        self.UKDLocationID = "gid://shopify/Location/61867622466"  # Shopify tag for shop location
        self.Stock = {}
        self.ProductInfo = {}
        self.BarcodeMap = {}  # Add barcode mapping
        self.LoadStock()

    def __DownloadStock(self):
        """Description: Downloads the latest stock sheets available on UKD website to local computer to be used with
        system."""
        try:
            print("\n=== Starting UKD File Download ===")
            
            # Download stock file
            stock_path = os.path.join("files/UKDStock.csv")
            if os.path.exists(stock_path):
                print(f"Removing existing stock file: {stock_path}")
                os.remove(stock_path)
            print("Downloading UKD stock file...")
            wget.download(UKDStockFileLink, stock_path)
            print("\nUKD stock file downloaded successfully")

            # Download data file
            data_path = os.path.join("files/UKDData.csv")
            if os.path.exists(data_path):
                print(f"Removing existing data file: {data_path}")
                os.remove(data_path)
            print("Downloading UKD data file...")
            wget.download(UKDDataFileLink, data_path)
            print("\nUKD data file downloaded successfully")
            
            # Verify files exist and show sizes
            if os.path.exists(stock_path):
                size = os.path.getsize(stock_path)
                print(f"Stock file size: {size} bytes")
            if os.path.exists(data_path):
                size = os.path.getsize(data_path)
                print(f"Data file size: {size} bytes")
                
            print("=== Download Complete ===\n")
            
        except Exception as e:
            print(f"Error downloading UKD files: {str(e)}")
            raise

    def LoadStock(self):
        try:
            print("\n=== Starting Data Load ===")
            data_file_path = os.path.join("files", "UKDData.csv")
            print(f"Loading UKD data from: {data_file_path}")
            
            if not os.path.exists(data_file_path):
                raise FileNotFoundError(f"Data file not found: {data_file_path}")
            
            with open(data_file_path, 'r', encoding='utf-8') as file:
                print("Reading file contents...")
                lines = file.readlines()
                print(f"Read {len(lines)} lines")
                
                if not lines:
                    raise ValueError("File is empty")
                
                headers = lines[0].strip().split(',')
                print(f"Headers found: {headers}")
                
                try:
                    # Find the indices for the columns we need
                    ean13_idx = headers.index('EAN13')
                    style_idx = headers.index('StyleNo')
                    size_idx = headers.index('Size')
                    brand_idx = headers.index('Brand')
                    name_idx = headers.index('Name')
                    stock_idx = headers.index('Stock')
                    
                    print(f"Column indices:")
                    print(f"- EAN13: {ean13_idx}")
                    print(f"- StyleNo: {style_idx}")
                    print(f"- Size: {size_idx}")
                    print(f"- Brand: {brand_idx}")
                    print(f"- Name: {name_idx}")
                    print(f"- Stock: {stock_idx}")
                    
                except ValueError as e:
                    print(f"Error finding columns: {str(e)}")
                    print(f"Available columns: {headers}")
                    raise
                
                print("\nProcessing data rows...")
                barcode_count = 0
                
                for line_num, line in enumerate(lines[1:], 1):  # Skip header row
                    fields = line.strip().split(',')
                    if len(fields) > max(ean13_idx, style_idx, size_idx, stock_idx):
                        # Clean up barcode - remove any whitespace and take only digits
                        raw_barcode = fields[ean13_idx].strip()
                        barcode = ''.join(c for c in raw_barcode if c.isdigit())
                        
                        # Only process if we have a valid 13-digit barcode
                        if len(barcode) == 13:
                            style_no = fields[style_idx].strip()
                            size = fields[size_idx].strip()
                            
                            # Handle stock value more robustly
                            stock_value = fields[stock_idx].strip()
                            try:
                                # Try to convert to integer, default to 0 if not possible
                                stock = int(stock_value) if stock_value.isdigit() else 0
                            except (ValueError, AttributeError):
                                stock = 0
                                
                            brand = fields[brand_idx].strip() if len(fields) > brand_idx else ''
                            name = fields[name_idx].strip() if len(fields) > name_idx else ''
                            
                            # Store stock information
                            sku = f"{style_no}-{size}"
                            self.Stock[sku] = stock
                            
                            # Store product information
                            if style_no not in self.ProductInfo:
                                self.ProductInfo[style_no] = {
                                    'brand': brand,
                                    'name': name
                                }
                            
                            # Map barcode to product info
                            self.BarcodeMap[barcode] = {
                                'styleNo': style_no,
                                'size': size,
                                'brand': brand,
                                'name': name
                            }
                            barcode_count += 1
                            
                            # Print every 1000th barcode for sampling
                            if barcode_count % 1000 == 0:
                                print(f"Processed {barcode_count} barcodes. Latest: {barcode} -> {style_no}-{size}")
                
                print(f"\nProcessing complete:")
                print(f"- Total barcodes loaded: {len(self.BarcodeMap)}")
                print(f"- Total products loaded: {len(self.ProductInfo)}")
                print(f"- Total SKUs loaded: {len(self.Stock)}")
                
                if len(self.BarcodeMap) > 0:
                    print("\nSample of loaded barcodes:")
                    sample_barcodes = list(self.BarcodeMap.items())[:3]
                    for barcode, info in sample_barcodes:
                        print(f"Barcode: {barcode}")
                        print(f"- Style No: {info['styleNo']}")
                        print(f"- Size: {info['size']}")
                        print(f"- Brand: {info['brand']}")
                        print(f"- Name: {info['name']}")
                        print("---")
                
                print("=== Data Load Complete ===\n")
                
        except Exception as e:
            print(f"Error loading UKD stock data: {str(e)}")
            self.Stock = {}
            self.ProductInfo = {}
            self.BarcodeMap = {}
            raise

    def GetFullStock(self):
        """Description: Reads all rows in stock sheet into Python to be used when updating stock"""
        try:
            StockList = {}
            stock_file_path = os.path.join("files/UKDStock.csv")
            
            if not os.path.exists(stock_file_path):
                raise FileNotFoundError(f"Stock file not found at {stock_file_path}")
                
            print(f"Reading stock data from {stock_file_path}")
            with open(stock_file_path, 'r') as File:  # opens stock sheet into Python
                Reader = csv.reader(File)  # created reader object to process csv
                for Row in Reader:
                    if len(Row) >= 2:  # Ensure row has at least 2 columns
                        StockList[Row[0].strip()] = Row[1].strip()  # Strip whitespace from product code
                        
            print(f"Loaded {len(StockList)} products from stock file")
            # Print first few entries to help with debugging
            items = list(StockList.items())[:5]
            print("Sample of stock data:")
            for code, stock in items:
                print(f"  {code}: {stock}")
                
            return StockList
        except Exception as e:
            print(f"Error reading stock file: {str(e)}")
            raise 

    def GetProductInfo(self, style_no):
        """Description: Gets product information from UKD data file for a specific SKU"""
        try:
            data_file_path = os.path.join("files/UKDData.csv")
            
            if not os.path.exists(data_file_path):
                print(f"Data file not found at {data_file_path}")
                raise FileNotFoundError(f"Data file not found at {data_file_path}")
            
            # Get the base product code (without size) and insert space after letter prefix
            base_code = style_no.split('-')[0] if '-' in style_no else style_no
            # Insert space after the letter prefix (e.g., 'B430' -> 'B 430')
            if len(base_code) > 1 and base_code[0].isalpha() and base_code[1].isdigit():
                base_code = f"{base_code[0]} {base_code[1:]}"
            
            print(f"Looking up product info for SKU: {style_no} (formatted base code: {base_code})")
            with open(data_file_path, 'r', encoding='utf-8-sig') as File:
                Reader = csv.reader(File)
                header = next(Reader)  # Skip and store header row
                print(f"CSV Headers: {header}")
                
                for Row in Reader:
                    if len(Row) >= 16:  # UKDData.csv has at least 16 columns
                        product_code = Row[0].strip()
                        if product_code == base_code:
                            print(f"Found matching product code: {product_code}")
                            print(f"Full row data: {Row}")
                            
                            try:
                                # Get the trade price from column 14
                                trade_price_raw = Row[14].strip()
                                print(f"Raw trade price value: '{trade_price_raw}'")
                                
                                # Remove currency symbol and commas
                                trade_price_clean = trade_price_raw.replace('£', '').replace(',', '').strip()
                                print(f"Cleaned trade price value: '{trade_price_clean}'")
                                
                                # Convert to float
                                trade_price = float(trade_price_clean) if trade_price_clean else 0.0
                                print(f"Converted trade price: {trade_price}")
                                
                                # Get VAT rate from column 15 and calculate VAT price
                                vat_code = Row[15].strip().upper()
                                vat_rate = {
                                    'S': 0.20,  # 20% Standard rate
                                    'R': 0.05,  # 5% Reduced rate
                                    'Z': 0.00   # 0% Zero rate
                                }.get(vat_code, 0.20)  # Default to standard rate if unknown
                                
                                print(f"VAT code: {vat_code}, VAT rate: {vat_rate}")
                                vat_price = trade_price * (1 + vat_rate)
                                print(f"Calculated VAT inclusive price: {vat_price}")
                                
                            except (ValueError, TypeError) as e:
                                print(f"Error converting prices: {e}")
                                trade_price = 0.0
                                vat_price = 0.0
                            
                            result = {
                                'brand': Row[1].strip(),
                                'name': Row[2].strip(),
                                'description': Row[5].strip(),
                                'tradePriceEx': f"{trade_price:.2f}",
                                'tradePriceInc': f"{vat_price:.2f}"
                            }
                            print(f"Returning product info: {result}")
                            return result
            
            print(f"No product information found for SKU: {style_no}")
            return None
            
        except Exception as e:
            print(f"Error reading product info: {str(e)}")
            raise 

    def GetProductFromBarcode(self, barcode):
        """Look up product information using EAN13 barcode"""
        print(f"\n=== Barcode Lookup ===")
        print(f"Looking up barcode: {barcode}")
        print(f"Total barcodes in map: {len(self.BarcodeMap)}")
        
        if len(self.BarcodeMap) == 0:
            print("Warning: Barcode map is empty!")
            return None
            
        result = self.BarcodeMap.get(barcode)
        
        if result:
            print("Found product:")
            print(f"- Style No: {result['styleNo']}")
            print(f"- Size: {result['size']}")
            print(f"- Brand: {result['brand']}")
            print(f"- Name: {result['name']}")
        else:
            print(f"No product found for barcode: {barcode}")
            print("Sample of available barcodes:")
            sample_barcodes = list(self.BarcodeMap.keys())[:3]
            print(f"- {', '.join(sample_barcodes)}")
            
        print("=== Lookup Complete ===\n")
        return result 