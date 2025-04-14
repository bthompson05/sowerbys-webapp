import requests
from bs4 import BeautifulSoup as BS
import json
import re
from ShopifyResources import ShopifyResources


class ComfortShoeWarehouse:

    def __init__(self):
        self.Global = GlobalSafety()
        self.GlobalStock = self.Global.product_dictionary
        self.V12 = V12Footwear()

    def DrawOptions(self, screen):
        pass

    def DownloadHTML(self, url):
        response = requests.get(url)
        with open('files/csw.html', 'wb+') as f:
            f.write(response.content)

    def ReadHTML(self):
        with open('files/csw.html', 'rb') as response:
            self.HTML = str(response.read())
        with open('files/csw.html', 'rb') as response:
            self.soup = BS(response.read(), 'html.parser')

    def GetHTML(self, url):
        return requests.get(url).text

    def ScrapePage(self, url):

        HTML = self.GetHTML(url)
        soup = BS(HTML, "html.parser")

        # Search for product ID using generic scraping
        id_index = HTML.find('id="ProductJson')
        # Create substring starting HTML only from id
        substring = HTML[id_index:]
        # Find end of id, given by >
        end_index = substring.find(">")
        # Trim rest of string, id= and " " just to give code
        product_json_id = substring[4:end_index - 1]

        # Gets product details from Shopify, in JSON
        product_details = soup.find(id=product_json_id)
        json_contents = json.loads(product_details.text)

        sku = self.ExtractSKU(url)
        vendor = json_contents['vendor']
        price = json_contents['price'] / 100
        title = json_contents['title']


        if sku in self.GlobalStock:
            images, copy = self.Global.ExtractData(self.GlobalStock[sku])
        elif self.V12.SearchSKU(sku):
            pass

        sizes = self.GetSizes(soup.find('select', {'id': 'option-size-uk'}))



        # check in case p is not included

        # Find the <td> with the text "Colour:"
        colour_td = soup.find('td', string=lambda x: x and 'Colour:' in x)
        # Find the adjacent <td> containing the color
        colour = colour_td.find_next_sibling('td').get_text(strip=True)

        return CSWProduct(title, copy, sku, vendor, sizes, price, colour, images)

    def ExtractSKU(self, url):
        match = re.search(r'\b[a-zA-Z]+-?\d+\b|\b\d+-?[a-zA-Z]+\b', url)

        if match:
            return match.group().replace('-', '')
        else:
            return None

    def GetSizes(self, soup):
        sizes = []

        # Extract options and their values
        options = soup.find_all('option')
        for option in options:
            size = option.get_text().strip()  # Get the text of the option and strip any surrounding whitespace
            sizes.append(size)

        return sizes

class CSWProduct:

    def __init__(self, title, description, sku, brand, sizes, cost, colour, images):
        self.CSWLocationID = "gid://shopify/Location/61867622466"  # Shopify tag for shop location

        self.Title, self.Description, self.SKU, self.Brand, self.Cost, self.Colour = title, description, sku, brand, cost, colour
        self.Sizes = sizes
        self.Images = images

        self.SalePrice = 0
    def ProduceVariantsList(self):

        Variants = '['
        for size in self.Sizes:
            main_image = self.Images[0]
            String = '''{mediaSrc: "%s", options: ["%s", "%s"], sku: "%s", price: %s, inventoryItem: {tracked: true, cost: %s}, inventoryPolicy: DENY, inventoryQuantities: [{locationId: "%s", availableQuantity: %s}]}''' % (
                main_image, self.Colour, size, self.SKU+"/"+size.zfill(2), self.SalePrice, self.Cost, self.CSWLocationID, 5)

            Variants += String
        Variants += ']'
        return Variants

    def AddProduct(self, name, price):
        self.SalePrice = price
        variants = self.ProduceVariantsList()
        ShopifyResources().AddProducts(name, self.Description, variants, self.BuildImageList(self.Images), self.Brand)

    def SetSalesPrice(self, price):
        self.SalePrice = price

    def BuildImageList(self, image_urls):

        images_string = '['

        for url in image_urls:
            String = '''{mediaContentType: IMAGE, originalSource:"%s"},''' % (url)
            images_string += String

        images_string += ']'
        return images_string
class GlobalSafety:

    def __init__(self):
        self.safety_footwear_link = "https://global-safety.co.uk/catalogue/safety-footwear/"
        self.product_dictionary = {}  # Store all products and their links once fully run

        self.get_all_products()

    def get_html(self, url):
        """Gets HTML code from the given url."""
        return requests.get(url).text

    def get_all_brands(self):
        """Gets all the brands of safety footwear stocked by GlobalSafety, returns a list of their links"""

        # Gets HTML for the products page, using link that can be changed
        html = self.get_html(self.safety_footwear_link)
        # Creates a BS object for the given page
        soup = BS(html, "html.parser")
        # Finds the area of the code containing an ul of the brands stocked
        brands_code = soup.find(class_="children")
        # Loops through each of the li items and pulls the href
        hrefs = [a['href'] for a in brands_code.find_all('a', href=True)]
        return hrefs

    def get_products_of_brand(self, brand_url):
        """Given a url for a brand, it loops through all their products, adding sku and url to dictionary"""

        # Gets the HTML code for each brand page
        html = self.get_html(brand_url)
        # Creates a BS object for the given page
        soup = BS(html, "html.parser")
        # Generated a list of all the li tags for each product by a given brand
        products = soup.find(class_="products").find_all('li', class_='product')
        # Loops through each product code in above list
        for product in products:
            # Adds key (image alt, which gives href) and value (url) to the product dictionary
            sku = str(product.find('img')['alt']).strip().lower()
            if sku[-1].isalpha():
                sku = sku[:-1]
            self.product_dictionary[sku] = product.find('a')['href']

    def get_all_products(self):
        """Driver code for generating the list of all products"""

        # Gets the list of urls for the brands stocked
        brands = self.get_all_brands()
        # Loops through each url for each brand and adds all products to dictionary
        for brand in brands:
            self.get_products_of_brand(brand)

    def ExtractData(self, url):
        HTML = self.get_html(url)
        soup = BS(HTML, "html.parser")
        images = self.FindImages(soup)
        summary = soup.find(class_="summary")
        title = summary.find("p")
        ul = summary.find("ul")
        if ul is None:
            ul = "<ul>"
            textBlock = title.find_next_sibling('p')
            bulletList = textBlock.decode_contents().strip("\n").split("<br/>")
            for bullet in bulletList:
                strippedBullet = bullet.strip("\n")
                ul += f"<li>{strippedBullet}</li>"
            ul += "</ul>"

        copy = f"{title}{ul}<p>Don't forget, we pay the postage! Shipped from our family run store in Stourbridge.</p>"
        return images, copy.replace("\n", "").replace("– ", "")

    def FindImages(self, soup):
        images = soup.find(id="product-gallery-main")
        image_urls = []

        # Extract the href attribute from each <a> tag within the div
        if images:
            anchor_tags = images.find_all('a')
            for tag in anchor_tags:
                href = tag.get('href')
                if href:
                    image_urls.append(href)

        return image_urls



class V12Footwear:

    def __init__(self):
        self.safety_footwear_link = "https://global-safety.co.uk/catalogue/safety-footwear/"
        self.V12_search_link = "https://v12footwear.com/search?q="

    def SearchSKU(self, SKU):
        response = requests.get(self.V12_search_link + "SKU")
        soup = BS(response.text, "html.parser")
        base = (soup.find('div', id='gf-products'))
        base.find("product-item-v1")
        print(base.find("product-item-v1"))
