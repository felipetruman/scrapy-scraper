#!/usr/bin/env python3

import datetime, sys, os, shutil, random, urllib.parse, tldextract, scrapy, scrapy.utils.project, scrapy.crawler, bs4, jsbeautifier, colorama, termcolor

start = datetime.datetime.now()

colorama.init(autoreset = True)

# ----------------------------------------

def unique(sequence):
	seen = set()
	return [x for x in sequence if not (x in seen or seen.add(x))]

default_encoding = "ISO-8859-1"

def read_file(file):
	tmp = []
	with open(file, "r", encoding = default_encoding) as stream:
		for line in stream:
			line = line.strip()
			if line:
				tmp.append(line)
	stream.close()
	return unique(tmp)

def write_array(data, out):
	confirm = "yes"
	if os.path.isfile(out):
		print(("'{0}' already exists").format(out))
		confirm = input("Overwrite the output file (yes): ")
	if confirm.lower() == "yes":
		try:
			with open(out, "w") as stream:
				for line in data:
					stream.write(str(line).strip() + "\n")
			stream.close()
			print(("Results have been saved to '{0}'").format(out))
		except FileNotFoundError:
			print(("Cannot save results to '{0}'").format(out))

default_user_agent = "Scrapy Scraper/1.1"

def get_random_user_agent():
	array = []
	file = os.path.join(os.path.abspath(os.path.split(__file__)[0]), "user_agents.txt")
	if os.path.isfile(file) and os.access(file, os.R_OK) and os.stat(file).st_size > 0:
		with open(file, "r", encoding = default_encoding) as stream:
			for line in stream:
				line = line.strip()
				if line:
					array.append(line)
		stream.close()
	return array[random.randint(0, len(array) - 1)] if array else default_user_agent

# ----------------------------------------

class ScrapyScraperSpider(scrapy.Spider):

	def __init__(
		self,
		urls,
		whitelist,
		playwright,
		agent,
		proxy,
		directory,
		out
	):
		self.name                  = "ScrapyScraperSpider"
		self.start_urls            = urls
		self.allowed_domains       = whitelist
		self.__playwright          = playwright
		self.__agent               = agent
		self.__proxy               = proxy
		self.__directory           = directory
		self.__out                 = out
		# --------------------------------
		# playwright's headless browser configuration
		self.__javascript_enabled  = True
		self.__accept_downloads    = False
		self.__bypass_csp          = False
		self.__ignore_https_errors = True
		self.__dont_filter         = False # send duplicate requests
		self.__context             = 0
		# --------------------------------
		self.__results             = []

	def start_requests(self):
		self.__print_start_urls()
		self.__print_allowed_domains()
		self.__print_info("Crawling and scraping...")
		self.__print_info("Press CTRL + C to exit early - results will be saved but please be patient")
		for url in self.start_urls:
			yield scrapy.Request(
				url         = url,
				headers     = self.__get_headers(),
				meta        = self.__get_meta(),
				errback     = self.__exception,
				callback    = self.__parse,
				dont_filter = self.__dont_filter
			)

	def closed(self, reason):
		self.__results = unique(self.__results)
		self.__print_info(("Total unique URLs crawled: {0}").format(len(self.__results)))
		if self.__results:
			write_array(sorted(self.__results, key = str.casefold), self.__out)

	def __print_start_urls(self):
		termcolor.cprint("Normalized start URLs:", "green")
		for url in self.start_urls:
			print(url)

	def __print_allowed_domains(self):
		if self.allowed_domains:
			termcolor.cprint("Allowed domains/subdomains:", "cyan")
			for domain in self.allowed_domains:
				print("*." + domain)
		else:
			termcolor.cprint("Domain whitelisting is off!", "red")

	def __print_info(self, text):
		termcolor.cprint(text, "yellow")

	def __get_headers(self):
		return {
			"Accept"                   : "*/*",
			"Accept-Language"          : "*",
			"Connection"               : "keep-alive",
			"Referer"                  : "https://www.google.com/",
			"Upgrade-Insecure-Requests": "1",
			"User-Agent"               : self.__agent
		}

	def __get_meta(self):
		tmp = self.__get_playwright_meta() if self.__playwright else {"proxy": self.__proxy}
		tmp["cookiejar"] = 1
		tmp["dont_merge_cookies"] = False
		return tmp

	def __get_playwright_meta(self):
		self.__context += 1
		tmp = {
			"playwright"                 : True,
			"playwright_context"         : str(self.__context),
			"playwright_context_kwargs"  : {
				"java_script_enabled": self.__javascript_enabled,
				"accept_downloads"   : self.__accept_downloads,
				"bypass_csp"         : self.__bypass_csp,
				"ignore_https_errors": self.__ignore_https_errors
			},
			"playwright_include_page"    : True,
			"playwright_page_goto_kwargs": {
				"wait_until": "load"
			}
		}
		if self.__proxy:
			tmp["playwright_context_kwargs"]["proxy"] = {
				"server": self.__proxy
			}
		return tmp

	async def __exception(self, failure):
		if self.__playwright:
			page = failure.request.meta["playwright_page"]
			await page.close()
			await page.context.close()

	async def __parse(self, response):
		if self.__playwright:
			page = response.meta["playwright_page"]
			await page.close()
			await page.context.close()
		self.__results.append(response.url)
		self.__download_js(response)
		print(response.url)
		for link in self.__extract_links(response):
			yield response.follow(
				url         = link,
				headers     = self.__get_headers(),
				meta        = self.__get_meta(),
				errback     = self.__exception,
				callback    = self.__parse,
				dont_filter = self.__dont_filter
			)

	def __download_js(self, response):
		if self.__directory:
			file = urllib.parse.urlparse(response.url).path.rsplit("/", 1)[-1]
			if file.lower().endswith(".js"):
				file = os.path.join(self.__directory, file)
				if not os.path.exists(file):
					try:
						soup = bs4.BeautifulSoup(response.body, "html.parser")
						open(file, "w").write(jsbeautifier.beautify(soup.get_text()))
					except Exception:
						pass

	def __extract_links(self, response):
		tmp = []
		for link in unique(scrapy.linkextractors.LinkExtractor(
			tags  = ["a", "link", "script"],
			attrs = ["href", "src"]
		).extract_links(response)):
			link = response.urljoin(link.url)
			if urllib.parse.urlparse(link).scheme.lower() in ["http", "https"]:
				tmp.append(link)
		return unique(tmp)

# ----------------------------------------

def page_block(request):
	return request.resource_type in ["fetch", "stylesheet", "image", "ping", "font", "media", "imageset", "beacon", "csp_report", "object", "texttrack", "manifest"]

class ScrapyScraper:

	def __init__(
		self,
		urls,
		whitelist,
		playwright,
		concurrent_requests,
		concurrent_requests_domain,
		auto_throttle,
		recursion,
		agent,
		proxy,
		directory,
		out
	):
		self.__urls                       = urls
		self.__whitelist                  = whitelist
		self.__playwright                 = playwright
		self.__concurrent_requests        = concurrent_requests
		self.__concurrent_requests_domain = concurrent_requests_domain
		self.__auto_throttle              = auto_throttle
		self.__recursion                  = recursion
		self.__agent                      = agent
		self.__proxy                      = proxy
		self.__directory                  = directory
		self.__out                        = out
		# --------------------------------
		# scrapy spider configuration
		self.__timeout                    = 30 # all timeouts
		self.__allow_retries              = False
		self.__max__retries               = 1
		self.__allow_redirects            = True
		self.__max_redirects              = 10
		self.__robots_obey                = False
		self.__headless_browser           = True
		self.__browser_type               = "chromium" # playwright's headless browser

	def run(self):
		settings = scrapy.utils.project.get_project_settings()
		# --------------------------------
		settings["COOKIES_ENABLED"] = True
		settings["DOWNLOAD_TIMEOUT"] = self.__timeout # connect / read timeout
		settings["RANDOMIZE_DOWNLOAD_DELAY"] = True
		if self.__proxy:
			settings["HTTPPROXY_ENABLED"] = True
		# --------------------------------
		if self.__auto_throttle:
			settings["EXTENSIONS"]["scrapy.extensions.throttle.AutoThrottle"] = 100
			settings["AUTOTHROTTLE_ENABLED"] = True
			settings["AUTOTHROTTLE_DEBUG"] = False
			settings["AUTOTHROTTLE_START_DELAY"] = 5
			settings["AUTOTHROTTLE_MAX_DELAY"] = 30
			settings["AUTOTHROTTLE_TARGET_CONCURRENCY"] = self.__auto_throttle
		# --------------------------------
		settings["CONCURRENT_REQUESTS"] = self.__concurrent_requests
		settings["CONCURRENT_REQUESTS_PER_DOMAIN"] = self.__concurrent_requests_domain
		settings["RETRY_ENABLED"] = self.__allow_retries
		settings["RETRY_TIMES"] = self.__max__retries
		settings["REDIRECT_ENABLED"] = self.__allow_redirects
		settings["REDIRECT_MAX_TIMES"] = self.__max_redirects
		settings["DEPTH_LIMIT"] = self.__recursion
		# --------------------------------
		settings["ROBOTSTXT_OBEY"] = self.__robots_obey
		settings["REQUEST_FINGERPRINTER_IMPLEMENTATION"] = "2.7"
		settings["TELNETCONSOLE_ENABLED"] = False
		settings["LOG_ENABLED"] = False
		# --------------------------------
		if self.__playwright:
			settings["TWISTED_REACTOR"] = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
			settings["DOWNLOAD_HANDLERS"]["https"] = "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler"
			settings["DOWNLOAD_HANDLERS"]["http"] = "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler"
			settings["PLAYWRIGHT_LAUNCH_OPTIONS"] = {
				"headless": self.__headless_browser
			}
			settings["PLAYWRIGHT_BROWSER_TYPE"] = self.__browser_type
			settings["PLAYWRIGHT_ABORT_REQUEST"] = page_block
			settings["PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT"] = self.__timeout * 1000
		# --------------------------------
		scrapy_scraper_spider = scrapy.crawler.CrawlerProcess(settings)
		scrapy_scraper_spider.crawl(ScrapyScraperSpider, self.__urls, self.__whitelist, self.__playwright, self.__agent, self.__proxy, self.__directory, self.__out)
		scrapy_scraper_spider.start()

# ----------------------------------------

# my own validation algorithm

class Validate:

	def __init__(self):
		self.__proceed = True
		self.__args    = {
			"urls"                      : None,
			"whitelist"                 : None,
			"playwright"                : None,
			"concurrent_requests"       : None,
			"concurrent_requests_domain": None,
			"auto_throttle"             : None,
			"recursion"                 : None,
			"agent"                     : None,
			"proxy"                     : None,
			"directory"                 : None,
			"out"                       : None
		}

	def __basic(self):
		self.__proceed = False
		print("Scrapy Scraper v1.1 ( github.com/ivan-sincek/scrapy-scraper )")
		print("")
		print("Usage:   scrapy-scraper -u urls                     -o out         [-d directory]")
		print("Example: scrapy-scraper -u https://example.com/home -o results.txt [-d downloads]")

	def __advanced(self):
		self.__basic()
		print("")
		print("DESCRIPTION")
		print("    Crawl and scrape websites")
		print("URLS")
		print("    File with URLs or a single URL to start crawling and scraping from")
		print("    -u <urls> - urls.txt | https://example.com/home | etc.")
		print("WHITELIST")
		print("    File with whitelisted domains to limit the scope")
		print("    Specify 'off' to disable domain whitelisting")
		print("    Default: domains extracted from URLs")
		print("    -w <whitelist> - whitelist.txt | off | etc.")
		print("PLAYWRIGHT")
		print("    Use Playwright's headless browser")
		print("    -p <playwright> - yes")
		print("CONCURRENT REQUESTS")
		print("    Number of concurrent requests")
		print("    Default: 30")
		print("    -cr <concurrent-requests> - 15 | 45 | etc.")
		print("CONCURRENT REQUESTS PER DOMAIN")
		print("    Number of concurrent requests per domain")
		print("    Default: 10")
		print("    -crd <concurrent-requests-domain> - 5 | 15 | etc.")
		print("AUTO THROTTLE")
		print("    Auto throttle crawling speed")
		print("    Specify value lesser than 1 to decrease the speed")
		print("    Specify value greater than 1 to increase the speed")
		print("    Specify 'off' to disable auto throttling")
		print("    Default: 1")
		print("    -at <auto-throttle> - 0.5 | 1.5 | off | etc.")
		print("RECURSION")
		print("    Recursion depth limit")
		print("    Specify '0' for no limit")
		print("    Default: 1")
		print("    -r <recursion> - 0 | 2 | 4 | etc.")
		print("AGENT")
		print("    User agent to use")
		print(("    Default: {0}").format(default_user_agent))
		print("    -a <agent> - curl/3.30.1 | etc.")
		print("PROXY")
		print("    Web proxy to use")
		print("    -x <proxy> - http://127.0.0.1:8080 | etc.")
		print("DIRECTORY")
		print("    Output directory")
		print("    All extracted JavaScript files will be saved in this directory")
		print("    -d <directory> - downloads | etc.")
		print("OUT")
		print("    Output file")
		print("    -o <out> - results.txt | etc.")

	def __print_error(self, msg):
		print(("ERROR: {0}").format(msg))

	def __error(self, msg, help = False):
		self.__proceed = False
		self.__print_error(msg)
		if help:
			print("Use -h for basic and --help for advanced info")

	def __validate_urls(self, urls):
		if not isinstance(urls, list):
			urls = [urls]
		tmp = []
		for url in urls:
			data = {
				"schemes": ["http", "https"],
				"scheme_error": [
					("URL scheme is required: {0}").format(url),
					("Supported URL schemes are 'http' and 'https': {0}").format(url)
				],
				"domain_error": ("Invalid domain name: {0}").format(url),
				"port_error": ("Port number is out of range: {0}").format(url)
			}
			obj = urllib.parse.urlsplit(url)
			if not obj.scheme:
				self.__error(data["scheme_error"][0])
			elif obj.scheme not in data["schemes"]:
				self.__error(data["scheme_error"][1])
			elif not obj.netloc:
				self.__error(data["domain_error"])
			elif obj.port and (obj.port < 1 or obj.port > 65535):
				self.__error(data["port_error"])
			else:
				tmp.append(obj.geturl()) # normalized
		return unique(tmp)

	def __validate_domains(self, urls):
		if not isinstance(urls, list):
			urls = [urls]
		tmp = []
		const = "."
		for url in urls:
			obj = tldextract.extract(url)
			if obj.domain and obj.suffix:
				domain = obj.domain + const + obj.suffix
				if obj.subdomain:
					domain = obj.subdomain + const + domain
				tmp.append(domain.lower())
		return unique(tmp)

	def __parse_float(self, string):
		tmp = None
		try:
			tmp = float(string)
		except ValueError:
			pass
		return tmp

	def __remove_directory(self, directory):
		success = True
		try:
			if os.path.exists(directory):
				shutil.rmtree(directory)
		except Exception:
			success = False
			self.__error(("Cannot remove '{0}' related directories/subdirectories and/or files").format(directory))
		return success

	def __create_directory(self, directory):
		success = True
		try:
			if not os.path.exists(directory):
				os.mkdir(directory)
		except Exception:
			success = False
			self.__error(("Cannot create '{0}' directory").format(directory))
		return success

	def __check_directory(self, directory):
		success = False
		overwrite = "yes"
		if os.path.exists(directory):
			print(("'{0}' directory already exists").format(directory))
			overwrite = input("Overwrite the output directory (yes): ")
		if overwrite.lower() == "yes" and self.__remove_directory(directory):
			success = self.__create_directory(directory)
		else:
			self.__proceed = False
		return success

	def __validate(self, key, value):
		value = value.strip()
		if len(value) > 0:
			# --------------------
			if key == "-u" and self.__args["urls"] is None:
				self.__args["urls"] = value
				if os.path.isfile(self.__args["urls"]):
					if not os.access(self.__args["urls"], os.R_OK):
						self.__error("File with URLs does not have read permission")
					elif not os.stat(self.__args["urls"]).st_size > 0:
						self.__error("File with URLs is empty")
					else:
						self.__args["urls"] = self.__validate_urls(read_file(self.__args["urls"]))
				else:
					self.__args["urls"] = self.__validate_urls(self.__args["urls"])
			# --------------------
			elif key == "-w" and self.__args["whitelist"] is None:
				self.__args["whitelist"] = value
				if self.__args["whitelist"].lower() == "off":
					self.__args["whitelist"] = []
				elif not os.path.isfile(self.__args["whitelist"]):
					self.__error("File with whitelisted domains does not exists")
				elif not os.access(self.__args["whitelist"], os.R_OK):
					self.__error("File with whitelisted domains does not have read permission")
				elif not os.stat(self.__args["whitelist"]).st_size > 0:
					self.__error("File with whitelisted domains is empty")
				else:
					self.__args["whitelist"] = self.__validate_domains(read_file(self.__args["whitelist"]))
					if not self.__args["whitelist"]:
						self.__error("No valid whitelisted domains were found") # fail-safe
			# --------------------
			elif key == "-p" and self.__args["playwright"] is None:
				self.__args["playwright"] = value.lower()
				if self.__args["playwright"] != "yes":
					self.__error("Specify 'yes' to use Playwright's headless browser")
			# --------------------
			elif key == "-cr" and self.__args["concurrent_requests"] is None:
				self.__args["concurrent_requests"] = value
				if not self.__args["concurrent_requests"].isdigit():
					self.__error("Number of concurrent requests must be numeric")
				else:
					self.__args["concurrent_requests"] = int(self.__args["concurrent_requests"])
					if self.__args["concurrent_requests"] < 1:
						self.__error("Number of concurrent requests must be greater than zero")
			# --------------------
			elif key == "-crd" and self.__args["concurrent_requests_domain"] is None:
				self.__args["concurrent_requests_domain"] = value
				if not self.__args["concurrent_requests_domain"].isdigit():
					self.__error("Number of concurrent requests per domain must be numeric")
				else:
					self.__args["concurrent_requests_domain"] = int(self.__args["concurrent_requests_domain"])
					if self.__args["concurrent_requests_domain"] < 1:
						self.__error("Number of concurrent requests per domain must be greater than zero")
			# --------------------
			elif key == "-at" and self.__args["auto_throttle"] is None:
				self.__args["auto_throttle"] = value.lower()
				if self.__args["auto_throttle"] == "off":
					self.__args["auto_throttle"] = 0
				else:
					self.__args["auto_throttle"] = self.__parse_float(self.__args["auto_throttle"])
					if not isinstance(self.__args["auto_throttle"], float):
						self.__error("Auto throttle must be numeric")
					elif self.__args["auto_throttle"] < 0:
						self.__error("Auto throttle must be greater than zero")
			# --------------------
			elif key == "-r" and self.__args["recursion"] is None:
				self.__args["recursion"] = value
				if not self.__args["recursion"].isdigit():
					self.__error("Recursion depth limit must be numeric")
				else:
					self.__args["recursion"] = int(self.__args["recursion"])
					if self.__args["recursion"] < 0:
						self.__error("Recursion depth limit must be equal to or greater than zero")
			# --------------------
			elif key == "-a" and self.__args["agent"] is None:
				self.__args["agent"] = value
				if self.__args["agent"].lower() == "random":
					self.__args["agent"] = get_random_user_agent()
			# --------------------
			elif key == "-x" and self.__args["proxy"] is None:
				self.__args["proxy"] = self.__validate_urls(value)
				if self.__args["proxy"]:
					self.__args["proxy"] = self.__args["proxy"][0]
			# --------------------
			elif key == "-d" and self.__args["directory"] is None:
				self.__args["directory"] = value
			# --------------------
			elif key == "-o" and self.__args["out"] is None:
				self.__args["out"] = value
			# --------------------

	def __check(self, argc):
		count = 0
		for key in self.__args:
			if self.__args[key] is not None:
				count += 1
		return argc - count == argc / 2

	def run(self):
		# --------------------
		argc = len(sys.argv) - 1
		# --------------------
		if argc == 0:
			self.__advanced()
		# --------------------
		elif argc == 1:
			if sys.argv[1] == "-h":
				self.__basic()
			elif sys.argv[1] == "--help":
				self.__advanced()
			else:
				self.__error("Incorrect usage", True)
		# --------------------
		elif argc % 2 == 0 and argc <= len(self.__args) * 2:
			for i in range(1, argc, 2):
				self.__validate(sys.argv[i], sys.argv[i + 1])
			if None in [self.__args["urls"], self.__args["out"]] or not self.__check(argc):
				self.__error("Missing a mandatory option (-u, -o) and/or optional (-w, -p, -cr, -crd, -at, -r, -a, -x, -d)", True)
		# --------------------
		else:
			self.__error("Incorrect usage", True)
		# --------------------
		if self.__proceed:
			if self.__args["whitelist"] is None:
				self.__args["whitelist"] = self.__validate_domains(self.__args["urls"])
			if self.__args["concurrent_requests"] is None:
				self.__args["concurrent_requests"] = 30
			if self.__args["concurrent_requests_domain"] is None:
				self.__args["concurrent_requests_domain"] = 10
			if self.__args["auto_throttle"] is None:
				self.__args["auto_throttle"] = 1
			if self.__args["recursion"] is None:
				self.__args["recursion"] = 1
			if self.__args["agent"] is None:
				self.__args["agent"] = default_user_agent
			if self.__args["directory"] is not None:
				self.__check_directory(self.__args["directory"])
		# --------------------
		return self.__proceed
		# --------------------

	def get_arg(self, key):
		return self.__args[key]

# ----------------------------------------

def main():
	validate = Validate()
	if validate.run():
		print("###########################################################################")
		print("#                                                                         #")
		print("#                           Scrapy Scraper v1.1                           #")
		print("#                                     by Ivan Sincek                      #")
		print("#                                                                         #")
		print("# Crawl and scrape websites.                                              #")
		print("# GitHub repository at github.com/ivan-sincek/scrapy-scraper.             #")
		print("# Feel free to donate ETH at 0xbc00e800f29524AD8b0968CEBEAD4cD5C5c1f105.  #")
		print("#                                                                         #")
		print("###########################################################################")
		scrapy_scraper = ScrapyScraper(
			validate.get_arg("urls"),
			validate.get_arg("whitelist"),
			validate.get_arg("playwright"),
			validate.get_arg("concurrent_requests"),
			validate.get_arg("concurrent_requests_domain"),
			validate.get_arg("auto_throttle"),
			validate.get_arg("recursion"),
			validate.get_arg("agent"),
			validate.get_arg("proxy"),
			validate.get_arg("directory"),
			validate.get_arg("out")
		)
		scrapy_scraper.run()
		print(("Script has finished in {0}").format(datetime.datetime.now() - start))

if __name__ == "__main__":
	main()
