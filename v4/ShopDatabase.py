import sqlite3
import os
import datetime
from ShopifyResources import ShopifyResources as Shop

class ShopDatabase():

    def __init__(self):
        self.ConnectDB()

    def ConnectDB(self):
        self.Connection = sqlite3.connect(os.path.join("StoreDB.db"))
        self.Cursor = self.Connection.cursor()
        self.Cursor.execute("""CREATE TABLE IF NOT EXISTS"Sales" (
                                "SaleID"	INTEGER NOT NULL UNIQUE,
                                "ProductID"	TEXT NOT NULL,
                                "SalePrice"	NUMERIC,
                                "Date"	TEXT,
                                "Payment"	TEXT,
                                PRIMARY KEY("SaleID" AUTOINCREMENT));""")
        self.Connection.commit()

    def RegisterNewSaleOrReturn(self, SKU, Price, ReturnKey, Payment):
        Date = datetime.date.today()
        if Price == '':
            SPrice = 0
        elif ReturnKey == 1:
            SPrice = -float(Price)
        else:
            SPrice = float(Price)
        self.Cursor.execute(f"INSERT INTO SALES(ProductID, SalePrice, Date, Payment)"
                            f"VALUES ('{SKU}', {SPrice}, '{Date}', '{Payment}')")
        Shopify = Shop()
        Shopify.ChangeStock(SKU, Shopify.ShopLocationID, 1 if ReturnKey == 1 else -1)
        self.Connection.commit()

    def CloseDatabase(self):
        self.Connection.commit()
        self.Connection.close()

    def GetRevenueByDateRange(self, Date1, Date2):
        self.Cursor.execute(f"""SELECT Sum(SalePrice) FROM Sales WHERE date BETWEEN '{Date1}' AND '{Date2}'""")
        Data = self.Cursor.fetchone()[0]
        if Data == None:
            Data = 0
        return [f"Revenue between {Date1} and {Date2}: £{round(Data, 2)}"]

    def GetProductsSoldInDateRange(self, Date1, Date2):
        self.Cursor.execute(
            f"""SELECT ProductID, SalePrice, Date, Payment FROM SALES WHERE SalePrice >= 0 AND date BETWEEN '{Date1}' AND '{Date2}'""")
        Data = self.Cursor.fetchall()
        if Data == []:
            return ['No products sold within date range.']
        Strings = []
        for SKU, Price, Date, Payment in Data:
            Strings.append(f"{SKU} sold for £{round(Price, 2)} on {Date} using {Payment}.")
        return Strings

    def GetReturnedProducts(self, Date1, Date2):
        self.Cursor.execute(
            f"""SELECT ProductID, SalePrice, Date, Payment FROM SALES WHERE SalePrice < 0 AND date BETWEEN '{Date1}' AND '{Date2}'""")
        Data = self.Cursor.fetchall()
        if Data == []:
            return ['No products returned within date range.']
        Strings = []
        for SKU, Price, Date, Payment in Data:
            Strings.append(f"{SKU} returned for £{round(Price, 2)} on {Date} using {Payment}.")
        return Strings

    def GetBestSellers(self, Date1, Date2):
        self.Cursor.execute(
            f"""SELECT Count(ProductID) as Number, ProductID, SUM(SalePrice) FROM Sales WHERE SalePrice >= 0 AND date BETWEEN '{Date1}' AND '{Date2}' GROUP BY ProductID ORDER BY Number LIMIT 5""")
        Data = self.Cursor.fetchall()
        if Data == []:
            return ['No products sold within date range.']
        Strings = []
        for Count, SKU, SalePrice in Data:
            Strings.append(f"{SKU} sold {Count} units for £{round(SalePrice, 2)}.")
        return Strings