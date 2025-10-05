import csv
import os
import wget
import logging
import time

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
                file_age = time.time() - os.path.getmtime(stock_path)
                week_in_seconds = 7 * 24 * 60 * 60  # 7 days in seconds
                if file_age > week_in_seconds:
                    print(f"Removing old stock file (age: {file_age/86400:.1f} days): {stock_path}")
                    os.remove(stock_path)
                    print("Downloading UKD stock file...")
                    wget.download(UKDStockFileLink, stock_path)
                    print("\nUKD stock file downloaded successfully")
                else:
                    print(f"Using existing stock file (age: {file_age/86400:.1f} days): {stock_path}")
                    return  # Skip download if file is less than a week old
            

            # Download data file
            data_path = os.path.join("files/UKDData.csv")
            if os.path.exists(data_path):
                file_age = time.time() - os.path.getmtime(data_path)
                week_in_seconds = 7 * 24 * 60 * 60  # 7 days in seconds
                if file_age > week_in_seconds:
                    print(f"Removing old data file (age: {file_age/86400:.1f} days): {data_path}")
                    os.remove(data_path)
                    print("Downloading UKD data file...")
                    wget.download(UKDDataFileLink, data_path)
                    print("\nUKD data file downloaded successfully")
                else:
                    print(f"Using existing data file (age: {file_age/86400:.1f} days): {data_path}")
                    return  # Skip download if file is less than a week old

            
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
                    # Add color index
                    color_idx = headers.index('Color') if 'Color' in headers else 3
                    # Add price and VAT indices
                    price_idx = headers.index('Price') if 'Price' in headers else 14
                    vat_idx = headers.index('VAT') if 'VAT' in headers else 15
                    
                    print(f"Column indices:")
                    print(f"- EAN13: {ean13_idx}")
                    print(f"- StyleNo: {style_idx}")
                    print(f"- Size: {size_idx}")
                    print(f"- Brand: {brand_idx}")
                    print(f"- Name: {name_idx}")
                    print(f"- Stock: {stock_idx}")
                    print(f"- Color: {color_idx}")
                    print(f"- Price: {price_idx}")
                    print(f"- VAT: {vat_idx}")
                    
                except ValueError as e:
                    print(f"Error finding columns: {str(e)}")
                    print(f"Available columns: {headers}")
                    raise
                
                print("\nProcessing data rows...")
                barcode_count = 0
                
                for line_num, line in enumerate(lines[1:], 1):  # Skip header row
                    fields = line.strip().split(',')
                    if len(fields) > max(ean13_idx, style_idx, size_idx, stock_idx, color_idx, price_idx, vat_idx):
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
                            color = fields[color_idx].strip() if len(fields) > color_idx else ''
                            
                            # Get price and VAT
                            try:
                                # Get price
                                price_raw = fields[price_idx].strip() if len(fields) > price_idx else '0'
                                price_clean = price_raw.replace('£', '').replace(',', '').strip()
                                price = float(price_clean) if price_clean else 0.0
                                
                                # Get VAT code and calculate VAT price
                                vat_code = fields[vat_idx].strip().upper() if len(fields) > vat_idx else 'S'
                                vat_rate = {
                                    'S': 0.20,  # 20% Standard rate
                                    'R': 0.05,  # 5% Reduced rate
                                    'Z': 0.00   # 0% Zero rate
                                }.get(vat_code, 0.20)  # Default to standard rate if unknown
                                vat_price = price * (1 + vat_rate)
                                
                                price_str = f"{price:.2f}"
                                vat_price_str = f"{vat_price:.2f}"
                            except (ValueError, TypeError):
                                price_str = "0.00"
                                vat_price_str = "0.00"
                            
                            # Store stock information
                            sku = f"{style_no}-{size}"
                            self.Stock[sku] = stock
                            
                            # Store product information
                            if style_no not in self.ProductInfo:
                                self.ProductInfo[style_no] = {
                                    'brand': brand,
                                    'name': name,
                                    'color': color,
                                    'tradePriceEx': price_str,
                                    'tradePriceInc': vat_price_str
                                }
                            
                            # Map barcode to product info
                            self.BarcodeMap[barcode] = {
                                'styleNo': style_no,
                                'size': size,
                                'brand': brand,
                                'name': name,
                                'color': color,
                                'tradePriceEx': price_str,
                                'tradePriceInc': vat_price_str,
                                'ean13': barcode
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
                        print(f"- Color: {info.get('color', 'N/A')}")
                        print(f"- Price (ex VAT): £{info.get('tradePriceEx', '0.00')}")
                        print(f"- Price (inc VAT): £{info.get('tradePriceInc', '0.00')}")
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
        """Description: Gets product information from UKD data file for a specific style number"""
        try:
            data_file_path = os.path.join("files/UKDData.csv")
            
            if not os.path.exists(data_file_path):
                print(f"Data file not found at {data_file_path}")
                raise FileNotFoundError(f"Data file not found at {data_file_path}")
            
            # Clean up the style number
            style_no = style_no.strip()
            # Remove any spaces from the style number
            style_no = style_no.replace(' ', '')
            
            print(f"Looking up product info for style number: {style_no}")
            
            with open(data_file_path, 'r', encoding='utf-8-sig') as File:
                Reader = csv.reader(File)
                header = next(Reader)  # Skip and store header row
                print(f"CSV Headers: {header}")
                
                # Find column indices
                try:
                    style_col = header.index('StyleNo')
                    brand_col = header.index('Brand')
                    name_col = header.index('Name')
                    upper_col = header.index('Upper')
                    desc_col = header.index('Desc')
                    sole_col = header.index('Sole')
                    
                    # Make sure we get the correct price column 
                    price_col = header.index('Price') if 'Price' in header else 14
                    vat_col = header.index('VAT') if 'VAT' in header else 15
                    
                    # Add color column index
                    color_col = header.index('Color') if 'Color' in header else 3
                    # Add EAN13 column index
                    ean13_col = header.index('EAN13') if 'EAN13' in header else 17
                    
                    print(f"Column indices for key fields:")
                    print(f"- StyleNo: {style_col}")
                    print(f"- Price: {price_col}")
                    print(f"- VAT: {vat_col}")
                    print(f"- Color: {color_col}")
                    print(f"- EAN13: {ean13_col}")
                    
                except ValueError as e:
                    print(f"Error finding required column in UKDData.csv: {e}")
                    raise ValueError(f"Missing required column in UKDData.csv: {e}")
                
                for Row in Reader:
                    if len(Row) > max(style_col, brand_col, name_col, upper_col, desc_col, sole_col, price_col, vat_col, color_col, ean13_col):
                        # Clean up the product code from the row for comparison
                        product_code = Row[style_col].strip().replace(' ', '')
                        
                        # Compare the cleaned codes
                        if product_code.upper() == style_no.upper():
                            print(f"Found matching product code: {product_code}")
                            print(f"Full row data: {Row}")
                            
                            try:
                                # Get the trade price from the price column
                                trade_price_raw = Row[price_col].strip() if len(Row) > price_col else '0'
                                print(f"Raw trade price value: '{trade_price_raw}'")
                                
                                # Remove currency symbol and commas
                                trade_price_clean = trade_price_raw.replace('£', '').replace(',', '').strip()
                                print(f"Cleaned trade price value: '{trade_price_clean}'")
                                
                                # Convert to float, handle different formats
                                try:
                                    trade_price = float(trade_price_clean) if trade_price_clean else 0.0
                                except ValueError:
                                    # Try another format if the first one fails
                                    print(f"Failed to convert price '{trade_price_clean}', trying alternative format")
                                    trade_price_clean = ''.join(c for c in trade_price_clean if c.isdigit() or c == '.')
                                    if '.' not in trade_price_clean and len(trade_price_clean) > 2:
                                        # Add decimal point if missing (e.g., 1995 -> 19.95)
                                        trade_price_clean = trade_price_clean[:-2] + '.' + trade_price_clean[-2:]
                                    trade_price = float(trade_price_clean) if trade_price_clean else 0.0
                                
                                print(f"Converted trade price: {trade_price}")
                                
                                # Get VAT rate from the VAT column
                                vat_code = Row[vat_col].strip().upper() if len(Row) > vat_col else 'S'
                                vat_rate = {
                                    'S': 0.20,  # 20% Standard rate
                                    'R': 0.05,  # 5% Reduced rate
                                    'Z': 0.00   # 0% Zero rate
                                }.get(vat_code, 0.20)  # Default to standard rate if unknown
                                
                                print(f"VAT code: {vat_code}, VAT rate: {vat_rate}")
                                vat_price = trade_price * (1 + vat_rate)
                                print(f"Calculated VAT inclusive price: {vat_price}")
                                
                                # Get color name and EAN13 barcode
                                color_name = Row[color_col].strip() if len(Row) > color_col else ''
                                ean13_code = Row[ean13_col].strip() if len(Row) > ean13_col else ''
                                
                                # Clean up EAN13 code (remove any non-digit characters)
                                cleaned_ean13 = ''.join(c for c in ean13_code if c.isdigit())
                                if cleaned_ean13:
                                    ean13_code = cleaned_ean13
                                
                            except (ValueError, TypeError) as e:
                                print(f"Error converting prices: {e}")
                                trade_price = 0.0
                                vat_price = 0.0
                                color_name = ''
                                ean13_code = ''
                            
                            result = {
                                'brand': Row[brand_col].strip(),
                                'name': Row[name_col].strip(),
                                'upper': Row[upper_col].strip(),
                                'description': Row[desc_col].strip(),
                                'sole': Row[sole_col].strip(),
                                'tradePriceEx': f"{trade_price:.2f}",
                                'tradePriceInc': f"{vat_price:.2f}",
                                'color': color_name,
                                'ean13': ean13_code
                            }
                            print(f"Returning product info: {result}")
                            return result
            
            print(f"No product information found for style number: {style_no}")
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
            print(f"- Color: {result.get('color', 'N/A')}")
        else:
            print(f"No product found for barcode: {barcode}")
            print("Sample of available barcodes:")
            sample_barcodes = list(self.BarcodeMap.keys())[:3]
            print(f"- {', '.join(sample_barcodes)}")
            
        print("=== Lookup Complete ===\n")
        return result 