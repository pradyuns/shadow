# Scraper network boundaries

HTTP scraping checks the initial URL and each redirect target, and fails closed if DNS cannot be resolved or resolves to a non-public address. Browser scraping checks the initial URL and requests observed by Playwright's routing, and blocks service workers. Firecrawl checks the initial URL before sending it to the provider.

These checks are defense in depth, not network isolation. The HTTP and browser clients resolve hostnames again when connecting, so a DNS answer may change after validation. Browser routing does not necessarily observe every redirect. Firecrawl performs its own requests and redirects remotely, outside this application's validation. Deploy workers with outbound network controls that deny access to internal, link-local, metadata, and other non-public destinations; use a trusted Firecrawl deployment and its network protections when enabling that integration.
