import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from pathlib import Path
from playwright._impl._api_types import TimeoutError


async def extract_data(html):
    soup = BeautifulSoup(html, "html.parser")

    # Number HS graduates who immediately enroll in a NY college and participate in TAP
    hs_grad_enroll_tap = soup.find_all("text", class_="large_label")[0].text

    # Data point description
    # Begin in fall | Return for spring | Return for 2nd year | 150% grad rate | 6 year grad rate
    # Didn't use generator because I need to index
    chart_data_points = [
        p.text for p in soup.find_all("text", class_="pop_text")
    ]
    return hs_grad_enroll_tap, chart_data_points


async def write_to_file(school_name, grads, chart_data):
    b_fall = chart_data[0]
    r_spring = chart_data[1]
    r_2nd = chart_data[2]
    on_time_grad = chart_data[3]
    _150_grad = chart_data[4]
    _6_year_grad = chart_data[5]

    out = f"{school_name},{grads},{b_fall},{r_spring},{r_2nd},{on_time_grad},{_150_grad},{_6_year_grad}\n"

    out_dir = "./out"

    #final_file = Path(out_dir) / school_name.replace("/", "_")
    final_file = Path(out_dir) / "2014_master.csv"
    with open(final_file, "a") as f:
        f.write(out)


async def generate_csv(page, name=None):
    # Generating the CSV file
    try:
        chart_select = page.locator("svg:has(text.large_label)").first
        hs_grad, CDP = await extract_data(await chart_select.inner_html())
        await write_to_file(name, hs_grad, CDP)
    except TimeoutError:
        # There is no data
        await write_to_file(name, 0, [0, 0, 0, 0, 0, 0])


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        source_url = "https://newyork.edtrust.org/to-and-through/#s=310600011540&y=2014"
        await page.goto(source_url)

        # To avoid interruptions set timeout to 30000
        # However by doing that, run time will drastically increase
        page.set_default_timeout(5000)

        # Page loads
        ## retrieving a list of schools

        # click the selector so the menu items will show up
        await page.locator("span.select2-selection__rendered").click()

        # now all available schools is rendered to page
        school_select = page.locator("ul.select2-results__options")

        # All valid options
        ops = school_select.locator("li")
        count = await ops.count()

        # manually set the starting point if scraping gets interrupted
        for i in range(count):
            # the menu is currently open
            school_name = await ops.nth(i).text_content()
            await ops.nth(i).click()
            task = asyncio.create_task(generate_csv(page, school_name))
            # open the menu again
            await page.locator("span.select2-selection__rendered").click()
            await task

        # Exit...
        await browser.close()


asyncio.run(main())
