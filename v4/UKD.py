import csv


import os
import wget

UKDStockFileLink = 'https://www.ukdistributors.co.uk/downloads/xStockFile2.csv'
UKDDataFileLink = 'https://www.ukdistributors.co.uk/downloads/xStockFile6.csv'
UKDImageLink = 'https://www.ukdistributors.co.uk/photos/840/'

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

class UKDStock:

    def __init__(self):
        self.__DownloadStock()  # Downloads latest stock each time program loaded
        self.ShopLocationID = "gid://shopify/Location/17633640514"  # Shopify tag for shop location
        self.UKDLocationID = "gid://shopify/Location/61867622466"  # Shopify tag for shop location
        pass

    def __DownloadStock(self):

        """Description: Downloads the latest stock sheets available on UKD website to local computer to be used with
        system."""

        if os.path.exists(os.path.join("files/UKDStock.csv")):  # if stock file already downloaded and in directory
            os.remove(os.path.join("files/UKDStock.csv"))  # remove file from directory
        wget.download(UKDStockFileLink, os.path.join("files/UKDStock.csv"))  # downloads sheet to local computer

        if os.path.exists(os.path.join("files/UKDData.csv")):  # if stock file already downloaded and in directory
            os.remove(os.path.join("files/UKDData.csv"))  # remove file from directory
        wget.download(UKDDataFileLink, os.path.join("files/UKDData.csv"))  # downloads sheet to local computer

    def GetFullStock(self):

        """Description: Reads all rows in stock sheet into Python to be used when updating stock"""

        StockList = {}
        with open(os.path.join("files/UKDStock.csv"), 'r') as File:  # opens stock sheet into Python
            Reader = csv.reader(File)  # created reader object to process csv
            for Row in Reader:
                StockList[Row[0]] = Row[1]

        return StockList

    def GetOutOfStock(self):
        Stock = []
        StockList = []
        with open(os.path.join("files/UKDStock.csv"), 'r') as File:
            Reader = csv.reader(File)
            for Row in Reader:
                print(Row[1])
                if Row[1] == "0":
                    Stock.append((Row[0], Row[1]))
                    StockList.append(Row[0])

        return StockList, Stock

    def GetReferences(self):

        self.References = {}
        with open(os.path.join('files/UKDData.csv'), 'r') as File:
            Reader = csv.reader(File)
            for Row in Reader:
                Header = Row
                break

        for i in range(len(Header)):
            self.References[Header[i]] = i

    def ReadBook(self):

        self.Book = []
        with open(os.path.join('files/UKDData.csv'), 'r') as File:
            Reader = csv.reader(File)
            for Row in Reader:
                self.Book.append(Row)

    def FindProducts(self, ProductID):
        self.GetReferences()
        self.ReadBook()
        Products = []
        for Row in self.Book:
            SKU = Row[self.References['StyleNo']].replace(" ", "")
            if SKU.startswith(ProductID):
                Products.append(Row)
        return Products

    def FindOptions(self, Products):
        Options = {'Colours': [], 'Sizes': []}
        for Row in Products:
            if Row[self.References['Color']] not in Options['Colours']:
                Options['Colours'].append(Row[self.References['Color']])
            if (Row[self.References['Size']]) not in Options['Sizes']:
                Size = Row[self.References['Size']]
                if Size == 'UK' or Size == 'EU':
                    Size = Row[self.References['Size'] + 1]
                Options['Sizes'].append(Size)

        Options['Colours'].sort()
        Options['Sizes'] = [float(x) for x in Options['Sizes']]
        Options['Sizes'].sort()
        Options['Sizes'] = [f"{x:g}" for x in Options['Sizes']]

        return Options

    def GetDetails(self, Products):

        Product = Products[0]
        TradePrice = Product[self.References['Price']]
        VAT = 0.2 if Product[self.References['VAT']] == 'S' else 0
        WithVat = round(float(TradePrice) * (1 + VAT), 2)

        if Product[self.References['Size']] == 'UK' or Product[self.References['Size']] == 'EU':
            TradePrice = Product[self.References['Price'] + 1]
            VAT = 0.2 if Product[self.References['VAT'] + 1] == 'S' else 0
            WithVat = round(float(TradePrice) * (1 + VAT), 2)

        Brand = Product[self.References['Brand']]
        ProductName = f"Description: {Product[self.References['Desc']]}, Name: {Product[self.References['Name']]}"
        return Brand, ProductName, TradePrice, WithVat

    def GetImages(self, Product):

        ImageLinks = []
        ImageOptions = [str(i) for i in range(2, 9)]
        ImageOptions.insert(0, '')

        for i in ImageOptions:
            try:

                Link = f"{UKDImageLink}{Product}{i}.jpg"
                wget.download(Link, os.path.join("TempImage.jpg"))
                os.remove(os.path.join('TempImage.jpg'))
                ImageLinks.append(Link)

            except Exception as Error:
                print(f"****** Error Occured - {Error} - {Link}")
                break

        return ImageLinks

    def AddImagesToProdcuts(self, Products):

        for Product in Products:
            if 'Images' not in Product:
                SKU = Product[self.References['StyleNo']]
                Images = self.GetImages(SKU)
                Product.append('Images')
                Product.append(Images)
                for Prod in Products:
                    if 'Images' not in Prod:
                        Product.append('Images')
                        Product.append(Images)

        return Products

    def GenerateImageList(self, Products):

        ImageList = []
        for Product in Products:
            Images = Product[-1]
            print(Product)
            for Image in Images:
                Link = Image.replace(' ', '%20')
                if Link not in ImageList:
                    ImageList.append(Link)

        return ImageList

    def GenerateInputImages(self, Images):
        ImagesString = '['

        for Image in Images:
            String = '''{mediaContentType: IMAGE, originalSource:"%s"},''' % (Image)
            ImagesString += String

        ImagesString += ']'
        return ImagesString

    def ProduceProductsFromOptions(self, Products, Options):
        Permutations = []
        for Col in Options['Colours']:
            for Size in Options['Sizes']:
                if (Col, Size) not in Permutations:
                    Permutations.append((Col, Size))


        ReturnList = []
        for Product in Products:
            Colour = Product[self.References['Color']]
            Size = Product[self.References['Size']]

            if (Colour, Size) in Permutations:
                ReturnList.append(Product)

        return ReturnList

    def GetDescriptionHTML(self, Product):

        Upper = Product[self.References['Upper']]
        Desc = Product[self.References['Desc']]
        Sole = Product[self.References['Sole']]
        try:
            int(Product[self.References['HSSCode']])
            HTML = f"<ul><li>{Upper} upper</li><li>{Desc}</li><li>{Sole} sole</li></ul><p>Don't forget, we pay the postage! Shipped from our family run store in Stourbridge.</p>"
        except:
            HTML = f"<ul><li>{Upper} upper</li><li>{Desc}</li><li>{Sole} sole</li><li>{Product[self.References['HSSCode']]}</li></ul><p>Don't forget, we pay the postage! Shipped from our family run store in Stourbridge.</p>"

        return HTML

    def ProduceVariantsList(self, Products, DefaultCostPrice, SalePrice, StoreStock):
        Products = sorted(Products, key=lambda d: float(d[self.References['Size']]))
        Variants = '['
        for Product in Products:
            Colour = Product[self.References['Color']]

            Size = Product[self.References['Size']]

            SKU = f"{Product[self.References['StyleNo']].replace(' ', '')}-{Size}"
            CostPrice = round(
                float(Product[self.References['Price']]) * (1 + float(0.2 if Product[self.References['VAT']] == "S" else 0)), 2)
            WarehouseStock = Product[self.References['Stock']]
            Image1 = Product[-1][0].replace(' ', '%20')
            print(Image1)
            if CostPrice != DefaultCostPrice:
                Difference = CostPrice - DefaultCostPrice
                SalePrice = round(float(SalePrice) + 2 * Difference, 2)

            if (Colour, Size) in StoreStock:
                Stock = StoreStock[(Colour, Size)]

                String = '''{mediaSrc: "%s", options: ["%s", "%s"], sku: "%s", price: %s, inventoryItem: {tracked: true, cost: %s}, inventoryPolicy: DENY, inventoryQuantities: [{locationId: "%s", availableQuantity: %s}, {locationId: "%s", availableQuantity: %s}]}''' % (
                Image1, Colour, Size, SKU, SalePrice, CostPrice, self.ShopLocationID, Stock,
                self.UKDLocationID, WarehouseStock)
            else:
                String = '''{mediaSrc: "%s", options: ["%s", "%s"], sku: "%s", price: %s, inventoryItem: {tracked: true, cost: %s}, inventoryPolicy: DENY, inventoryQuantities: [{locationId: "%s", availableQuantity: %s}]}''' % (
                Image1, Colour, Size, SKU, SalePrice, CostPrice, self.UKDLocationID, WarehouseStock)

            Variants += String
        Variants += ']'
        return Variants
