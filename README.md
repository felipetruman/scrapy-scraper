# Scrapy Scraper

Web crawler and scraper based on Scrapy and Playwright's headless browser.

To use the headless browser specify `-p yes` flag. Browsers, unlike other standard web request libraries, have the ability to render JavaScript encoded HTML content.

To automatically download and beautify all JavaScript files, including minified ones, specify `-d downloads` flag - where `downloads` is your desired output directory.

Resources:

* [scrapy.org](https://scrapy.org) (official)
* [playwright.dev](https://playwright.dev/python/docs/intro) (official)
* [scrapy/scrapy](https://github.com/scrapy/scrapy) (GitHub)
* [scrapy-plugins/scrapy-playwright](https://github.com/scrapy-plugins/scrapy-playwright) (GitHub)

Tested on Kali Linux v2023.3 (64-bit).

Made for educational purposes. I hope it will help!

## Table of Contents

* [How to Install](#how-to-install)
* [How to Build and Install Manually](#how-to-build-and-install-manually)
* [How to Run](#how-to-run)
* [Usage](#usage)

## How to Install

```bash
pip3 install scrapy-scraper

pip3 install --upgrade scrapy-scraper

playwright install chromium
```

## How to Build and Install Manually

Run the following commands:

```bash
git clone https://github.com/ivan-sincek/scrapy-scraper && cd scrapy-scraper

python3 -m pip install --upgrade build

python3 -m build

python3 -m pip install dist/scrapy-scraper-1.1-py3-none-any.whl

playwright install chromium
```

## How to Run

Restricted (auto throttling and domain whitelisting is on):

```fundamental
scrapy-scraper -u https://example.com/home -o results.txt -a random -d js
```

Unrestricted (auto throttling and domain whitelisting is off):

```fundamental
scrapy-scraper -u https://example.com/home -o results.txt -a random -d js -at off -w off
```

## Usage

```fundamental
Scrapy Scraper v1.1 ( github.com/ivan-sincek/scrapy-scraper )

Usage:   scrapy-scraper -u urls                     -o out         [-d directory]
Example: scrapy-scraper -u https://example.com/home -o results.txt [-d downloads]

DESCRIPTION
    Crawl and scrape websites
URLS
    File with URLs or a single URL to start crawling and scraping from
    -u <urls> - urls.txt | https://example.com/home | etc.
WHITELIST
    File with whitelisted domains to limit the scope
    Specify 'off' to disable domain whitelisting
    Default: domains extracted from URLs
    -w <whitelist> - whitelist.txt | off | etc.
PLAYWRIGHT
    Use Playwright's headless browser
    -p <playwright> - yes
CONCURRENT REQUESTS
    Number of concurrent requests
    Default: 30
    -cr <concurrent-requests> - 15 | 45 | etc.
CONCURRENT REQUESTS PER DOMAIN
    Number of concurrent requests per domain
    Default: 10
    -crd <concurrent-requests-domain> - 5 | 15 | etc.
AUTO THROTTLE
    Auto throttle crawling speed
    Specify value lesser than 1 to decrease the speed
    Specify value greater than 1 to increase the speed
    Specify 'off' to disable auto throttling
    Default: 1
    -at <auto-throttle> - 0.5 | 1.5 | off | etc.
RECURSION
    Recursion depth limit
    Specify '0' for no limit
    Default: 1
    -r <recursion> - 0 | 2 | 4 | etc.
AGENT
    User agent to use
    Default: Scrapy Scraper/1.1
    -a <agent> - curl/3.30.1 | etc.
PROXY
    Web proxy to use
    -x <proxy> - http://127.0.0.1:8080 | etc.
DIRECTORY
    Output directory
    All extracted JavaScript files will be saved in this directory
    -d <directory> - downloads | etc.
OUT
    Output file
    -o <out> - results.txt | etc.
```
