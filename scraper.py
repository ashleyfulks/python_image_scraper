import asyncio
import csv
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError

async def fetch_product_details(page, url):
    try:
        print(f"Navigating to {url}...")
        await page.goto(url, timeout=5000)  # 5-second timeout for navigation
        
        # Check for out of stock status
        stock_selector = "p.📚19-7-0uGevg.📚19-7-0EEwzY"
        stock_element = await page.query_selector(stock_selector)
        if stock_element:
            stock_text = await stock_element.inner_text()
            if "Out of stock" in stock_text:
                print("Product is out of stock. Skipping.")
                return None, None, None

        # Check for placeholder indicating no images
        placeholder_selector = "div.figure__placeholder-bg"
        placeholder_element = await page.query_selector(placeholder_selector)
        if placeholder_element:
            print("No product images available. Skipping.")
            return None, None, None
    
        print("Waiting for network to be idle...")
        await page.wait_for_load_state('networkidle', timeout=10000)  # 10-second timeout for network idle
    except PlaywrightTimeoutError:
        print("Timeout occurred, processing what is available...")
    except PlaywrightError as e:
        print(f"Playwright error occurred: {e}")
        return None, None, None
    
    try:
        print("Extracting product name and image URLs...")
        
        # Extract product name
        name_selector = "h1.w-product-title"  # Updated selector for the product name
        name_element = await page.query_selector(name_selector)
        product_name = await name_element.inner_text() if name_element else "Name not found"
        # Print the product name
        print(f"Product name: {product_name}")
        
        # Extract product image URLs
        image_selector = "#bb240244-f7c5-11ec-a611-571561743ede > div > div > div.w-cell.fullwidth-mobile.no-margin-top.no-overflow.row > div > div > div > div.product-gallery__wrapper > div > div.display-desktop > div > div img"
        images = await page.query_selector_all(image_selector)
        
        image_urls = []
        if images:
            print(f"Found {len(images)} product images")
            for img in images:
                src = await img.get_attribute('src')
                if src:
                    # Strip query parameters to get the highest resolution URL if applicable
                    highest_res_src = src.split('?')[0]
                    image_urls.append(highest_res_src)
        else:
            print("No product images found.")
        
        return url.split('/')[-1], product_name, image_urls
    except PlaywrightError as e:
        print(f"Error extracting product details: {e}")
        return None, None, None

async def main():
    input_csv = "./files/NBAHype_product_links.csv"
    output_csv = "./files/product_images.csv"
    products_with_no_images_csv = "./files/products_with_no_images.csv"
    
    # Read product titles and Shopify IDs from the provided CSV file
    valid_products = set()
    with open(products_with_no_images_csv, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            valid_products.add(row['product_title'])

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # headless=False to visually debug if needed
        page = await browser.new_page()
        
        # Read product links from CSV
        with open(input_csv, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            product_links = [row['link'] for row in reader]
        
        # Prepare output CSV
        with open(output_csv, mode='w', newline='') as csvfile:
            fieldnames = ['product_id', 'product_link', 'product_handle', 'product_name', 'product_images']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for link in product_links:
                print(f"Processing {link}")
                product_id, product_name, product_images = await fetch_product_details(page, link)
                if not product_name or not product_images:
                    continue

                # Check if the product name is in the valid products set
                if product_name not in valid_products:
                    print(f"Product '{product_name}' not in the valid products list. Skipping.")
                    continue
                
                product_handle = link.replace("https://www.nwahype.com/product/", "").replace(f"/{product_id}", "")
                product_images_str = ','.join(product_images)
                
                writer.writerow({
                    'product_id': product_id,
                    'product_link': link,
                    'product_handle': product_handle,
                    'product_name': product_name,
                    'product_images': product_images_str
                })
        
        print("Closing browser...")
        await browser.close()

    print("Script completed.")

asyncio.run(main())
