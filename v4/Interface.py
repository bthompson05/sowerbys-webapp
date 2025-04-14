import datetime
import time
import tkinter as Tk
from tkinter import ttk, Toplevel
from PIL import Image, ImageTk
from Modules import Calendar
from threading import Thread
from ShopifyResources import ShopifyResources as Shop
from ShopDatabase import ShopDatabase
from Gardiners import GardinersStock
from ComfortShoe import ComfortShoeWarehouse
from UKD import UKDStock
import os


class Page(Tk.Frame):
    def __init__(self, *args, **kwargs):
        Tk.Frame.__init__(self, *args, **kwargs)

    def show(self):
        self.lift()

    def DisplayText(self, Frame, Text):
        Label = Tk.Label(Frame, text=Text)
        Label.pack()

    def ClearFrame(self, Frame):
        for Widgets in Frame.winfo_children():
            Widgets.destroy()

class AddProducts(Page):
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        self.ProductFrame = Tk.Frame(self)
        self.Gardiners = GardinersStock()
        self.CSW = ComfortShoeWarehouse()
        self.UKD = UKDStock()
        self.Shopify = Shop()

        Label = Tk.Label(self.ProductFrame,
                         text="Choose the distributor to get stock from:")
        Label.pack()

        self.OptionsChoice = Tk.ttk.Combobox(self.ProductFrame, state="readonly",
                                       values=['Gardiners', 'UK Distributors', 'Comfort Shoe Warehouse'],
                                       width=50)
        self.OptionsChoice.pack()

        ProductCode = Tk.Frame(self.ProductFrame)
        ProductCodeText = Tk.Label(ProductCode, text='Product Code:  ')
        self.ProductCodeField = Tk.Entry(ProductCode, width=20)
        ProductCodeText.pack(side='left')
        self.ProductCodeField.pack(side='left')
        ProductCode.pack()

        Label = Tk.Label(self.ProductFrame,
                         text="Note: If choosing comfort shoe, rather than using the product code, paste a link to the product on CSW website.")
        Label.pack()

        SelectButton = Tk.Button(self.ProductFrame, text='Search Product', command=self.ReturnSelection)
        SelectButton.pack()

        self.OptionsFrame = Tk.Frame(self.ProductFrame)

        self.ProductFrame.pack()


    def ReturnSelection(self):
        Selection = self.OptionsChoice.get()
        self.OptionsFrame.destroy()
        if Selection == 'Gardiners':
            self. Products = self.Gardiners.FindProducts(self.ProductCodeField.get().capitalize())
            self.Options = self.Gardiners.FindOptions(self.Products)
            self.Brand, ProductName, TradePrice, RRP, self.WithVat = self.Gardiners.GetDetails(self.Products)

            self.OptionsFrame = Tk.Frame(self.ProductFrame)

            self.DisplayText(self.OptionsFrame, f"Brand: {self.Brand}, {ProductName}")
            self.DisplayText(self .OptionsFrame, f"TradePrice (exc VAT): £{TradePrice} (inc VAT): £{self.WithVat}, RRP: £{RRP}")

            for Key in self.Options:
                self.DisplayText(self.OptionsFrame, f"{Key} has the following options: {', '.join(self.Options[Key])}")
            self.DisplayText(self.OptionsFrame, f"Initial Number of Variants: {(len(self.Products))}   (must be less that 100)")
            self.DisplayText(self.OptionsFrame, "____________________________________________________________________________________")

            self.OptionsFrame.pack()

            ProductName = Tk.Frame(self.OptionsFrame)
            ProductNameText = Tk.Label(ProductName, text='Enter Name for Product Listing:  ')
            self.ProductNameField = Tk.Entry(ProductName, width=20)
            ProductNameText.pack(side='left')
            self.ProductNameField.pack(side='left')
            ProductName.pack()

            Price = Tk.Frame(self.OptionsFrame)
            PriceText = Tk.Label(Price, text='Price:  ')
            self.PriceField = Tk.Entry(Price, width=20)
            PriceText.pack(side='left')
            self.PriceField.pack(side='left')
            Price.pack()

            self.ExclusionsFrame = Tk.Frame(self.OptionsFrame)
            self.Exclusions = []

            ExclusionsBoxFrame = Tk.Frame(self.ExclusionsFrame)
            ExclusionsText = Tk.Label(ExclusionsBoxFrame, text='Enter an exclusion from the above options:  ')
            self.ExclusionsField = Tk.Entry(ExclusionsBoxFrame, width=20)
            ExclusionsText.pack(side='left')
            self.ExclusionsField.pack(side='left')
            ExclusionsBoxFrame.pack(side='left')

            self.ExclusionsAddedFrame = Tk.Frame(self.ExclusionsFrame)
            self.ExclusionsFrame.pack()

            ExclusionButton = Tk.Button(self.ExclusionsFrame, text='Add Exclusion', command=lambda: self.RemoveOption(self.ExclusionsField.get()))
            ExclusionButton.pack()

            self.SowerbysStockFrame = Tk.Frame(self.OptionsFrame)
            StockAtSowerbys = Tk.Checkbutton(self.SowerbysStockFrame, text="Stock in store?", command=self.GetSowerbysStock)
            StockAtSowerbys.pack()
            self.SowerbysStockFrame.pack()

            self.Stock = {}
            ConfirmButton = Tk.Button(self.OptionsFrame, text='Add Product',
                               command= lambda : self.AddProduct('Gardiners', self.ProductNameField.get(), self.PriceField.get(), self.Stock))
            ConfirmButton.pack()

            self.ExclusionsFrame.pack()
        if Selection == 'UK Distributors':
            self.Products = self.UKD.FindProducts(self.ProductCodeField.get().upper())
            self.Options = self.UKD.FindOptions(self.Products)
            self.Brand, ProductName, TradePrice, self.WithVat = self.UKD.GetDetails(self.Products)

            self.OptionsFrame = Tk.Frame(self.ProductFrame)

            self.DisplayText(self.OptionsFrame, f"Brand: {self.Brand}, {ProductName}")
            self.DisplayText(self.OptionsFrame,
                             f"TradePrice (exc VAT): £{TradePrice} (inc VAT): £{self.WithVat}")

            #self.Products = self.UKD.AddImagesToProdcuts(self.Products)
            #print(self.Products)

            for Key in self.Options:
                self.DisplayText(self.OptionsFrame, f"{Key} has the following options: {', '.join(self.Options[Key])}")
            self.DisplayText(self.OptionsFrame,
                             f"Initial Number of Variants: {(len(self.Products))}   (must be less that 100)")
            self.DisplayText(self.OptionsFrame,
                             "____________________________________________________________________________________")

            self.OptionsFrame.pack()

            ProductName = Tk.Frame(self.OptionsFrame)
            ProductNameText = Tk.Label(ProductName, text='Enter Name for Product Listing:  ')
            self.ProductNameField = Tk.Entry(ProductName, width=60)
            ProductNameText.pack(side='left')
            self.ProductNameField.pack(side='left')
            ProductName.pack()

            Price = Tk.Frame(self.OptionsFrame)
            PriceText = Tk.Label(Price, text='Price:  ')
            self.PriceField = Tk.Entry(Price, width=20)
            PriceText.pack(side='left')
            self.PriceField.pack(side='left')
            Price.pack()

            self.ExclusionsFrame = Tk.Frame(self.OptionsFrame)
            self.Exclusions = []

            ExclusionsBoxFrame = Tk.Frame(self.ExclusionsFrame)
            ExclusionsText = Tk.Label(ExclusionsBoxFrame, text='Enter an exclusion from the above options:  ')
            self.ExclusionsField = Tk.Entry(ExclusionsBoxFrame, width=20)
            ExclusionsText.pack(side='left')
            self.ExclusionsField.pack(side='left')
            ExclusionsBoxFrame.pack(side='left')

            self.ExclusionsAddedFrame = Tk.Frame(self.ExclusionsFrame)
            self.ExclusionsFrame.pack()

            ExclusionButton = Tk.Button(self.ExclusionsFrame, text='Add Exclusion',
                                        command=lambda: self.RemoveOption(self.ExclusionsField.get()))
            ExclusionButton.pack()

            self.SowerbysStockFrame = Tk.Frame(self.OptionsFrame)
            StockAtSowerbys = Tk.Checkbutton(self.SowerbysStockFrame, text="Stock in store?",
                                             command=self.GetSowerbysStock)
            StockAtSowerbys.pack()
            self.SowerbysStockFrame.pack()

            self.Stock = {}
            ConfirmButton = Tk.Button(self.OptionsFrame, text='Add Product',
                                      command=lambda: self.AddProduct('UKD', self.ProductNameField.get(),
                                                                      self.PriceField.get(), self.Stock))
            ConfirmButton.pack()

        if Selection == "Comfort Shoe Warehouse":
            product = self.CSW.ScrapePage(self.ProductCodeField.get())


            self.OptionsFrame = Tk.Frame(self.ProductFrame)

            self.DisplayText(self.OptionsFrame, f"Brand: {product.Brand}, {product.Title}")
            self.DisplayText(self.OptionsFrame,
                             f"TradePrice (exc VAT): £{product.Cost} (inc VAT): £{product.Cost * 1.2}")

            self.DisplayText(self.OptionsFrame, f"{product.SKU} is available in sizes {', '.join(product.Sizes)}")

            self.DisplayText(self.OptionsFrame,
                             "____________________________________________________________________________________")

            self.OptionsFrame.pack()

            ProductName = Tk.Frame(self.OptionsFrame)
            ProductNameText = Tk.Label(ProductName, text='Enter Name for Product Listing:  ')
            self.ProductNameField = Tk.Entry(ProductName, width=60)
            ProductNameText.pack(side='left')
            self.ProductNameField.pack(side='left')
            ProductName.pack()

            Price = Tk.Frame(self.OptionsFrame)
            PriceText = Tk.Label(Price, text='Price:  ')
            self.PriceField = Tk.Entry(Price, width=20)
            PriceText.pack(side='left')
            self.PriceField.pack(side='left')
            Price.pack()


            ConfirmButton = Tk.Button(self.OptionsFrame, text='Add Product',
                                      command=lambda: product.AddProduct(self.ProductNameField.get(),
                                                                      self.PriceField.get()))
            ConfirmButton.pack()


    def GetSowerbysStock(self):
        self.Stock = {}
        StockFrame = Tk.Frame(self.SowerbysStockFrame)

        SizeText = Tk.Label(StockFrame, text='Size:  ')
        self.SizeField = Tk.Entry(StockFrame, width=10)
        SizeText.pack(side='left')
        self.SizeField.pack(side='left')

        ColourText = Tk.Label(StockFrame, text='Colour:  ')
        self.ColourField = Tk.Entry(StockFrame, width=10)
        ColourText.pack(side='left')
        self.ColourField.pack(side='left')

        QuantityText = Tk.Label(StockFrame, text='Quantity:  ')
        self.QuantityField = Tk.Entry(StockFrame, width=10)
        QuantityText.pack(side='left')
        self.QuantityField.pack(side='left')

        AddStockButton = Tk.Button(StockFrame, text='Add Product',
                                  command=lambda: AddStock())
        AddStockButton.pack()

        StockFrame.pack()

        def AddStock():
            Size = self.SizeField.get()
            Colour = self.ColourField.get()
            Quantity = self.QuantityField.get()

            if (Size != '' and Colour != '' and Quantity != '') and Size in self.Options['Sizes'] and Colour in self.Options['Colours']:
                self.Stock[(Colour, Size)] = Quantity
                self.DisplayText(self.SowerbysStockFrame, f"Added {Quantity} in stock for Size {Size} in {Colour}.")

    def RemoveOption(self, Option):

        print(self.Products)

        for Key in self.Options:
            if Option in self.Options[Key]:
                self.Options[Key].remove(Option)
                self.Exclusions.append(Option)

        self.Products = self.Gardiners.ProduceProductsFromOptions(self.Products, self.Options)

        self.ExclusionsAddedFrame.destroy()
        self.ExclusionsAddedFrame = Tk.Frame(self.OptionsFrame)
        self.DisplayText(self.ExclusionsAddedFrame, f"Exclusions Added: {', '.join(self.Exclusions)}")
        self.ExclusionsAddedFrame.pack()
        self.DisplayText(self.ExclusionsAddedFrame, f"Total Variants: {len(self.Products)}   (must be less that 100)")

    def AddProduct(self, Stockist, Title, Price, StoreStock):
        if Stockist == 'Gardiners':
            Variants = self.Gardiners.ProduceVariantsList(self.Products, self.WithVat, Price, StoreStock)
            Gallery = self.Gardiners.GenerateImageGallery(self.Products)
            ImagesInput = self.Gardiners.GenerateInputImages(self.Gardiners.GenerateImageList(Gallery))
            Description = self.Gardiners.GenerateProductCopyHTML(self.Products[0])

        elif Stockist == 'UKD':
            self.Products = self.UKD.AddImagesToProdcuts(self.Products)
            Variants = self.UKD.ProduceVariantsList(self.Products, self.WithVat, Price, StoreStock)
            Description = self.UKD.GetDescriptionHTML(self.Products[0])
            ImagesInput = self.UKD.GenerateInputImages(self.UKD.GenerateImageList(self.Products))


        self.Shopify.AddProducts(Title, Description, Variants, ImagesInput, self.Brand.title())
        self.OptionsFrame.destroy()



class ShopifyStock(Page):
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)

        self.ProductSearchFrame = Tk.Frame(self)
        Label = Tk.Label(self.ProductSearchFrame,
                         text="Find the stock availability for a product. Enter the product code and size:")
        Label.pack()

        ProductCode = Tk.Frame(self.ProductSearchFrame)
        ProductCodeText = Tk.Label(ProductCode, text='Product Code:  ')
        self.ProductCodeField = Tk.Entry(ProductCode, width=20)
        ProductCodeText.pack(side='left')
        self.ProductCodeField.pack(side='left')
        ProductCode.pack()

        Size = Tk.Frame(self.ProductSearchFrame)
        SizeText = Tk.Label(Size, text='Size:  ')
        self.SizeField = Tk.Entry(Size, width=20)
        SizeText.pack(side='left')
        self.SizeField.pack(side='left')
        Size.pack()

        SearchButton = Tk.Button(self.ProductSearchFrame, text='Select', command=self.StockSearch)
        SearchButton.pack()

        self.Results = Tk.Frame(self.ProductSearchFrame)
        self.ProductSearchFrame.pack()


        Label = Tk.Label(self,
                         text="Update the stock database for Shopify with the latest from the distributors. Choose the relevant option:")
        Label.pack()

        self.Options = Tk.ttk.Combobox(self, state="readonly",
                                       values=['UKD Stock Update'],
                                       width=50)
        self.Options.pack()

        SelectButton = Tk.Button(self, text='Select', command=self.ReturnSelection)
        SelectButton.pack()

        self.ProgressFrame = Tk.Frame(self)

        self.Shopify = Shop()
        self.TimeElapsed = 0
        self.Percentage = 0

    def StockSearch(self):
        self.Results.destroy()
        self.Results = Tk.Frame(self.ProductSearchFrame)
        SKU = f'{self.ProductCodeField.get().upper()}-{self.SizeField.get()}'
        Values = self.Shopify.FetchTotalInventoryLevel(SKU)
        for Value in Values:
            self.DisplayText(self.Results, Value)
        self.Results.pack()

    def ReturnSelection(self):
        Selection = self.Options.get()
        if Selection == 'UKD Stock Update':
            print('Created Thread for Stock Update.')
            self.Update = Thread(target=self.Shopify.UKDStockUpdate)

            self.Update.daemon = True
            self.Update.start()

            self.ClearFrame(self.ProgressFrame)
            self.ProgressFrame = Tk.Frame(self)
            self.ProgressBar = ttk.Progressbar(self.ProgressFrame, orient="horizontal", length=300, mode='determinate')
            self.ProgressBar.pack(side='left')

            self.ProgressText = Tk.Label(self.ProgressFrame, text="0%")
            self.ProgressText.pack(side='left')

            self.TimeElapsedText = Tk.Label(self.ProgressFrame, text=f"Time Elapsed: {0}")
            self.TimeElapsedText.pack()

            self.ProgressFrame.pack()

            self.TimeBegun = time.time()
            UpdateProgress = Thread(target=self.UpdateProgress)
            UpdateProgress.start()

        else:
            return None
    def UpdateProgress(self):
        Percentage = 0
        self.ProgressBar['value'] = Percentage
        while Percentage < 100:
            TimeElapsed = str(datetime.timedelta(seconds=round(time.time() - self.TimeBegun)))
            self.TimeElapsedText.config(text=f"Time Elapsed:{TimeElapsed}")
            self.ProgressText.config(text=f"{Percentage}%")

            Percentage = self.Shopify.PercentageComplete
            self.ProgressBar['value'] = Percentage

        if not self.Update.is_alive():
            self.ProgressText.config(text=f"100%")
            self.update_idletasks()

class StoreStock(Page):
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)

        Label = Tk.Label(self, text="Register a sale/refund in store. Choose the relevant option:")
        Label.pack()

        self.Options = Tk.ttk.Combobox(self, state="readonly", values=['Sale', 'Return', 'Add New Stock', 'Set In Shop Stock'], width=50)
        self.Options.pack()

        ProductCode = Tk.Frame(self)
        ProductCodeText = Tk.Label(ProductCode, text='Product Code:  ')
        self.ProductCodeField = Tk.Entry(ProductCode, width=20)
        ProductCodeText.pack(side='left')
        self.ProductCodeField.pack(side='left')
        ProductCode.pack()

        Size = Tk.Frame(self)
        SizeText = Tk.Label(Size, text='Size:  ')
        self.SizeField = Tk.Entry(Size, width=20)
        SizeText.pack(side='left')
        self.SizeField.pack(side='left')
        Size.pack()

        SalePrice = Tk.Frame(self)
        SalePriceText = Tk.Label(SalePrice, text='Sale Price (ignoring £ sign):  ')
        self.SalePriceField = Tk.Entry(SalePrice, width=20)
        SalePriceText.pack(side='left')
        self.SalePriceField.pack(side='left')
        SalePrice.pack()

        Quantity = Tk.Frame(self)
        QuantityText = Tk.Label(Quantity, text='Quantity:  ')
        self.QuantityField = Tk.Entry(Quantity, width=20)
        self.QuantityField.insert(0, "1")
        QuantityText.pack(side='left')
        self.QuantityField.pack(side='left')
        Quantity.pack()

        self.PaymentOptions = Tk.Frame(self)
        self.Payment = Tk.StringVar()
        self.Payment.set('Card')

        Tk.Radiobutton(self.PaymentOptions, variable=self.Payment, text='Card', value='Card').pack(side='left')
        Tk.Radiobutton(self.PaymentOptions, variable=self.Payment, text='Cash', value='Cash').pack(side='left')
        self.PaymentOptions.pack()

        SelectButton = Tk.Button(self, text='Update', command=self.ReturnSelection)
        SelectButton.pack()

        self.Response = Tk.Frame(self)

        self.Shopify = Shop()
        self.DB = ShopDatabase()

    def ReturnSelection(self):
        Selection = self.Options.get()
        SKU = f"{self.ProductCodeField.get().upper()}-{self.SizeField.get()}"
        Price = self.SalePriceField.get()
        Quantity = self.QuantityField.get()
        Payment = self.Payment.get()

        self.Response.destroy()
        self.Response = Tk.Frame(self)

        if Selection == 'Sale':
            if Quantity == '':
                self.DisplayText(self.Response, f"Please enter stock for {SKU}.")
            else:
                for i in range(int(Quantity)):
                    self.DB.RegisterNewSaleOrReturn(SKU, Price, 0, Payment)
                    self.DisplayText(self.Response, f"Registered new sale of {SKU} for £{Price}.")
        elif Selection == 'Return':
            if Quantity == '':
                self.DisplayText(self.Response, f"Please enter stock for {SKU}.")
            else:
                for i in range(int(Quantity)):
                    self.DB.RegisterNewSaleOrReturn(SKU, Price, 1, Payment)
                    self.DisplayText(self.Response, f"Registered new return of {SKU} for £{Price}.")
        elif Selection == 'Add New Stock':
            if Quantity == '':
                self.DisplayText(self.Response, f"Please enter stock for {SKU}.")
            else:
                for i in range(int(Quantity)):
                    self.Shopify.ChangeStock(SKU, self.Shopify.ShopLocationID, 1)
                    self.DisplayText(self.Response, f"Added 1 stock unit for {SKU} to Sowerbys store stock.")
        elif Selection == 'Set In Shop Stock':
            if Quantity == '':
                self.DisplayText(self.Response, f"Please enter stock for {SKU}.")
            else:
                self.Shopify.SetStock(SKU, self.Shopify.ShopLocationID, Quantity)
                self.DisplayText(self.Response, f"Set total stock for {SKU} at Sowerbys Shoes to {Quantity}.")

        self.Response.pack()

class SaleBook(Page):
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)

        Label = Tk.Label(self, text="Register a sale/refund in store. Choose the relevant option:")
        Label.pack()

        Options = ['Revenue In Date Period', 'Sales In Date Period', 'Returned Products', 'Best Sellers']
        self.Options = Tk.ttk.Combobox(self, state="readonly", values=Options, width=50)
        self.Options.pack()

        Label = Tk.Label(self, text="Enter the date period for the above option:")
        Label.pack()

        Date1 = Tk.Frame(self)
        Date1Text = Tk.Label(Date1, text='Date 1:   ')
        self.Date1Field = Tk.Entry(Date1, width=20)
        self.Date1Field.bind("<1>", self.PickDate1)
        Date1Text.pack(side='left')
        self.Date1Field.pack(side='left')
        Date1.pack()

        Date2 = Tk.Frame(self)
        Date2Text = Tk.Label(Date2, text='Date 2:   ')
        self.Date2Field = Tk.Entry(Date2, width=20)
        self.Date2Field.bind("<1>", self.PickDate2)
        Date2Text.pack(side='left')
        self.Date2Field.pack(side='left')
        Date2.pack()

        SelectButton = Tk.Button(self, text='Select', command=self.ReturnSelection)
        SelectButton.pack()

        self.DB = ShopDatabase()
        self.DataFrame = Tk.Frame(self)

    def ReturnSelection(self):
        Selection = self.Options.get()
        self.ClearFrame(self.DataFrame)
        Date1 = self.Date1Field.get()
        Date2 = self.Date2Field.get()
        Data = []
        if Selection == 'Revenue In Date Period':
            Data = self.DB.GetRevenueByDateRange(Date1, Date2)
        elif Selection == 'Sales In Date Period':
            Data = self.DB.GetProductsSoldInDateRange(Date1, Date2)
        elif Selection == 'Returned Products':
            Data = self.DB.GetReturnedProducts(Date1, Date2)
        elif Selection == 'Best Sellers':
            Data = self.DB.GetBestSellers(Date1, Date2)
        for Items in Data:
            self.DisplayText(self.DataFrame, Items)

        self.DataFrame.pack()

    def PickDate1(self, event):
        self.DateWindow1 = Toplevel()
        self.DateWindow1.grab_set()
        self.DateWindow1.title('Choose A Date')
        self.DateWindow1.geometry('250x220+590+370')
        self.Calendar1 = Calendar(self.DateWindow1, selectmode="day", date_pattern="yyyy-mm-dd")
        self.Calendar1.pack()

        SubmitButton = Tk.Button(self.DateWindow1, text='Submit', command=self.GrabDate1)
        SubmitButton.pack()

    def PickDate2(self, event):
        self.DateWindow2 = Toplevel()
        self.DateWindow2.grab_set()
        self.DateWindow2.title('Choose A Date')
        self.DateWindow2.geometry('250x220+590+370')
        self.Calendar2 = Calendar(self.DateWindow2, selectmode="day", date_pattern="yyyy-mm-dd")
        self.Calendar2.pack()

        SubmitButton = Tk.Button(self.DateWindow2, text='Submit', command=self.GrabDate2)
        SubmitButton.pack()

    def GrabDate1(self):
        self.Date1Field.delete(0, last=12)
        self.Date1Field.insert(0, self.Calendar1.get_date())
        self.DateWindow1.destroy()

    def GrabDate2(self):
        self.Date2Field.delete(0, last=12)
        self.Date2Field.insert(0, self.Calendar2.get_date())
        self.DateWindow2.destroy()


class MainView(Tk.Frame):
    def __init__(self, *args, **kwargs):
        Tk.Frame.__init__(self, *args, **kwargs)
        P1 = AddProducts(self)
        P2 = ShopifyStock(self)
        P3 = StoreStock(self)
        P4 = SaleBook(self)

        Container = Tk.Frame(self)
        ButtonFrame = Tk.Frame(HeaderFrame)
        Container.pack(side="top", fill="both", expand=True)
        ButtonFrame.pack()

        P1.place(in_=Container, x=0, y=0, relwidth=1, relheight=1)
        P2.place(in_=Container, x=0, y=0, relwidth=1, relheight=1)
        P3.place(in_=Container, x=0, y=0, relwidth=1, relheight=1)
        P4.place(in_=Container, x=0, y=0, relwidth=1, relheight=1)

        B1 = Tk.Button(ButtonFrame, text="Add Stock", command=P1.show)
        B2 = Tk.Button(ButtonFrame, text="Shopify Stock", command=P2.show)
        B3 = Tk.Button(ButtonFrame, text="Store Stock", command=P3.show)
        B4 = Tk.Button(ButtonFrame, text="Sale Book", command=P4.show)

        B1.pack(side="left")
        B2.pack(side="left")
        B3.pack(side="left")
        B4.pack(side="left")

        P1.show()


Root = Tk.Tk()
Root.wm_geometry("800x800")
Root.title(os.path.join('Sowerbys Shoes Stock System'))
Root.iconbitmap(os.path.join('Logo.ico'))

HeaderFrame = Tk.Frame(Root, width=800, height=300)
HeaderFrame.pack()
HeaderFrame.place()

LogoImage = ImageTk.PhotoImage(Image.open(os.path.join('Logo.png')))
ImageLabel = Tk.Label(HeaderFrame, image=LogoImage)
ImageLabel.pack()

main = MainView(Root)
main.pack(side="top", fill="both", expand=True)
Root.mainloop()
