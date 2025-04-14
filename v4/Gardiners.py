import csv
import os

import requests

import wget

stockList = []
GardinersStockLink = 'https://www.gardinerbros.co.uk/datafeeds/Productdata_b2b.csv'

class GardinersStock:
    def __init__(self):
        self.DownloadBook()
        self.GetReferences()
        self.ReadBook()
        self.ShopLocationID = "gid://shopify/Location/17633640514"
        self.GardinersLocationID = "gid://shopify/Location/61870899266"

    def DownloadBook(self):
        print("doing")
        if os.path.exists(os.path.join("files/GardinersData.csv")):  # if stock file already downloaded and in directory
            os.remove(os.path.join("files/GardinersData.csv"))  # remove file from directory
        response = requests.get(GardinersStockLink, stream=True)

        with open(os.path.join("files/GardinersData.csv"), "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    def GetReferences(self):

        self.References = {}
        with open(os.path.join('files/GardinersData.csv'), 'r') as File:
            Reader = csv.reader(File)
            for Row in Reader:
                Header = Row
                break

        for i in range(len(Header)):
            self.References[Header[i]] = i


    def ReadBook(self):

        self.Book = []
        with open(os.path.join('files/GardinersData.csv'), 'r') as File:
            Reader = csv.reader(File)
            for Row in Reader:
                self.Book.append(Row)

    def FindProducts(self, ProductID):

        Products = []
        for Row in self.Book:
            if Row[self.References['ProductID']] == str(ProductID):
                Products.append(Row)
        return Products

    def FindOptions(self, Products):
        Options = {'Colours': [], 'Sizes': []}
        for Row in Products:
            if Row[self.References['Colour Extention']] not in Options['Colours']:
                Options['Colours'].append(Row[self.References['Colour Extention']])
            if (Row[self.References['UK Size']]) not in Options['Sizes']:
                Options['Sizes'].append(Row[self.References['UK Size']])
        if '' in Options['Sizes']:
            Options['Sizes'] = []
            for Row in Products:
                if Row[self.References['EU Size']] not in Options['Sizes']:
                    Options['Sizes'].append(Row[self.References['EU Size']])
        Options['Colours'].sort()
        Options['Sizes'] = [float(x) for x in Options['Sizes']]
        Options['Sizes'].sort()
        Options['Sizes'] = [f"{x:g}" for x in Options['Sizes']]

        return Options

    def GetDetails(self, Products):

        Product = Products[0]
        TradePrice = Product[self.References['Trade Price']]
        RRP = Product[self.References['SRP']]
        VAT = Product[self.References['VAT']]
        WithVat = round(float(TradePrice) * (1 + float(VAT)), 2)

        Brand = Product[self.References['Brand']]
        ProductName = f"Short Product Name: {Product[self.References['Short Product Name']]}, Long Product Name: {Product[self.References['Long Product Name']]}"
        return Brand, ProductName, TradePrice, RRP, WithVat

    def GetSize(self, Product):
        return Product[self.References['UK Size']]

    def GetColour(self, Product):
        return Product[self.References['Colour Extention']]

    def GenerateProductCopyHTML(self, Product):
        CopyList = []
        Finished = False
        Prefix = "Main Copy"
        Iteration = 1
        CopyList.append(Product[self.References['InspirationalCopy']])
        while not Finished:
            Copy = Product[self.References[f"{Prefix} {Iteration}"]]
            if Copy == '':
                Finished = True
            else:
                for String in CopyList:
                    if Copy in String:
                        pass
                else:
                    CopyList.append(Product[self.References[f"{Prefix} {Iteration}"]])
                    Iteration += 1

        HtmlCopy = f"<p>{CopyList[0]}</p>"
        if len(HtmlCopy)> 1:
            HtmlCopy += "<ul>"
        for String in CopyList[1::]:
            HtmlCopy += f"<li>{String}</li>"
        if len(HtmlCopy)> 1:
            HtmlCopy += "</ul>"

        HtmlCopy += "<p>Don't forget, we pay the postage! Shipped from our family run store in Stourbridge.</p>"
        return HtmlCopy

    def GenerateImageGallery(self, Products):

        Gallery = {}
        for Product in Products:
            Colour = Product[self.References['Colour Extention']]
            if Colour not in Gallery:
                Gallery[Colour] = []

            for ImageOption in range(1,9):
                ImageLink = Product[self.References[f"Image{ImageOption}"]]
                if ImageLink != '':
                    if ImageLink not in Gallery[Colour]:
                        Gallery[Colour].append(ImageLink)

        return Gallery

    def GenerateImageList(self, Gallery):

        ImageList = []
        for Key in Gallery:
            Images = Gallery[Key]
            for Image in Images:
                if Image not in ImageList:
                    ImageList.append(Image)

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
            Colour = Product[self.References['Colour Extention']]
            Size = Product[self.References['UK Size']]
            if Size == '':
                Size = Product[self.References['EU Size']]

            if (Colour, Size) in Permutations:
                ReturnList.append(Product)

        return ReturnList


    def ProduceVariantsList(self, Products, DefaultCostPrice, SalePrice, StoreStock):
        Products = sorted(Products, key= lambda d: float(d[self.References['UK Size']]))
        Variants = '['
        for Product in Products:
            Colour = Product[self.References['Colour Extention']]

            Size = Product[self.References['UK Size']]
            if Size == '':
                Size = Product[self.References['EU Size']]

            SKU = Product[self.References['Product Reference']]
            Weight = Product[self.References['Weight']]
            CostPrice = round(float(Product[self.References['Trade Price']]) * (1 + float(Product[self.References['VAT']])), 2)
            WarehouseStock = Product[self.References['Stock']]
            Image1 = Product[self.References['Image1']]
            if CostPrice != DefaultCostPrice:
                Difference = CostPrice - DefaultCostPrice
                SalePrice = round(SalePrice + 2*Difference, 2)

            if (Colour, Size) in StoreStock:
                Stock = StoreStock[(Colour, Size)]

                String = '''{mediaSrc: "%s", options: ["%s", "%s"], sku: "%s", price: %s, weight: %s, inventoryItem: {tracked: true, cost: %s}, inventoryPolicy: DENY, inventoryQuantities: [{locationId: "%s", availableQuantity: %s}, {locationId: "%s", availableQuantity: %s}]}'''  % (Image1, Colour, Size, SKU, SalePrice, Weight, CostPrice, self.ShopLocationID, Stock, self.GardinersLocationID, WarehouseStock)
            else:
                String = '''{mediaSrc: "%s", options: ["%s", "%s"], sku: "%s", price: %s, weight: %s, inventoryItem: {tracked: true, cost: %s}, inventoryPolicy: DENY, inventoryQuantities: [{locationId: "%s", availableQuantity: %s}]}''' % (Image1, Colour, Size, SKU, SalePrice, Weight, CostPrice, self.GardinersLocationID, WarehouseStock)

            Variants += String
        Variants += ']'
        return Variants
