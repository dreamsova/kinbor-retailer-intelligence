"""Offline product evidence boundaries; no fixture is a live research claim."""
import json
import unittest
from unittest.mock import patch

import research
from test_direct_research import SyntheticResponse, SyntheticTransport, fetch_result, page, URL, KEY
from test_research import PUBLIC_DNS
import tinyfish_client


STAMP = '2026-11-10T02:00:00Z'


def product_page(**extra):
    result = {'url': URL + 'products/floral-grid-notebook',
              'title': 'Floral Grid Notebook', 'text': 'Price: USD 12.50',
              'status': 'ok', 'retrieved_at_utc': STAMP, 'links': []}
    result.update(extra)
    return result


class ProductEvidenceBoundaries(unittest.TestCase):
    def test_public_http_metadata_only_product_is_preserved_without_image_download(self):
        url = 'https://www.wonderfairhomeshopping.com/opossum-notepad.html'
        response = SyntheticResponse({})
        response.url = url
        response.headers = {'Content-Type': 'text/html'}
        response.body = (b'<title>Opossum Notepad - Wonder Fair</title>'
            b'<meta property="og:type" content="product">'
            b'<meta property="og:title" content="Opossum Notepad">'
            b'<meta property="og:image" content="https://cdn.shoplightspeed.com/notepad.jpg">'
            b'<meta property="product:price:amount" content="8.00">'
            b'<meta property="product:price:currency" content="USD">')
        with patch.object(research.socket, 'getaddrinfo', return_value=PUBLIC_DNS), \
                patch.object(research, 'build_opener') as opener:
            opener.return_value.open.return_value = response
            captured = research.fetch_page(url)
        self.assertEqual(opener.return_value.open.call_count, 1)
        row = research.product_observations([captured])[0]
        self.assertEqual(row['product_image_url'], 'https://cdn.shoplightspeed.com/notepad.jpg')
        self.assertEqual((row['public_price'], row['currency']), ('8.00', 'USD'))

    def test_jsonld_product_retains_exact_price_currency_and_image_reference(self):
        parser = research.PageParser()
        parser.feed('<script type="application/ld+json">' + json.dumps({
            '@graph': [{'@type': 'Product', 'name': 'Floral Grid Notebook',
                'description': 'A floral cover and ruled paper notebook.',
                'image': 'https://cdn.shopify.com/s/files/notebook.webp?v=123',
                'brand': {'name': 'Fixture Brand'},
                'offers': {'price': '12.50', 'priceCurrency': 'USD',
                           'availability': 'https://schema.org/InStock'}}]}) + '</script>')
        p = product_page(product_data=parser.product_data)
        rows = research.product_observations([p], 'public_http')
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['public_price'], '12.50')
        self.assertEqual(row['currency'], 'USD')
        self.assertEqual(row['brand_label'], 'Fixture Brand')
        self.assertEqual(row['product_image_url'], 'https://cdn.shopify.com/s/files/notebook.webp')
        self.assertEqual(row['source_url'], p['url'])
        self.assertEqual(row['retrieved_at_utc'], STAMP)
        self.assertEqual(row['observed_style_terms'], ['floral', 'grid', 'ruled'])
        for field in ('current_inventory', 'brand_relationship', 'buyer_interest',
                      'sales_authorization', 'image_reuse_permission', 'visible_style_features'):
            self.assertEqual(row[field], 'Unknown')
        self.assertEqual(research.normalize_page(research.normalize_page(p)), research.normalize_page(p))

    def test_navigation_terms_logo_and_dollar_symbol_do_not_invent_product_facts(self):
        p = product_page(title='Plain Notebook', text='Navigation: colorful floral fountain pen\n$12.50',
                         images=[{'url': '/logo.png', 'alt': 'Store logo'}])
        row = research.product_observations([p])[0]
        self.assertEqual(row['observed_style_terms'], [])
        self.assertEqual(row['product_image_url'], 'Unknown')
        self.assertEqual(row['public_price'], 'Unknown')
        self.assertEqual(row['currency'], 'Unknown')
        self.assertEqual(row['description_excerpt'], 'Unknown')

    def test_collection_and_failed_pages_do_not_create_product_observations(self):
        collection = product_page(url=URL + 'collections/notebooks')
        failed = product_page(status='failed')
        self.assertEqual(research.product_observations([collection, failed]), [])

    def test_public_product_focus_keeps_robots_and_official_domain_boundaries(self):
        allowed = URL + 'products/notebook'
        disallowed = URL + 'products/private-notebook'
        home = product_page(url=URL, links=[{'url': allowed, 'text': 'Notebook'},
            {'url': disallowed, 'text': 'Notebook'},
            {'url': 'https://unlinked-fixture.org/products/notebook', 'text': 'Notebook'}])
        robots = product_page(url=URL + 'robots.txt', text='User-agent: *\nDisallow: /products/private-notebook')
        public = product_page(url=allowed)
        lookup = {URL: home, URL + 'robots.txt': robots, allowed: public}
        with patch.object(research.socket, 'getaddrinfo', return_value=PUBLIC_DNS), \
                patch.object(research, 'fetch_page', side_effect=lambda url, **_: research.normalize_page(lookup[url])) as fetch:
            capture = research.public_capture(URL, product_focus=True)
        fetched = [call.args[0] for call in fetch.call_args_list]
        self.assertEqual(fetched, [URL + 'robots.txt', URL, allowed])
        self.assertEqual(capture['status'], 'partial')
        self.assertEqual(len(research.product_observations(capture['pages'])), 1)

    def test_wonderfair_html_discovery_is_domain_scoped_and_title_suffix_is_exact(self):
        self.assertTrue(research.is_product_url('https://www.wonderfairhomeshopping.com/opossum-notepad.html'))
        self.assertFalse(research.is_product_url('https://other-fixture.org/opossum-notepad.html'))
        self.assertFalse(research.is_product_url('https://www.wonderfairhomeshopping.com/privacy-policy.html'))
        p = product_page(url='https://www.wonderfairhomeshopping.com/opossum-notepad.html',
                         title='Opossum Notepad - Wonder Fair Home Shopping Network')
        row = research.product_observations([p])[0]
        self.assertEqual(row['title'], 'Opossum Notepad')
        self.assertEqual(research.product_title('Pink | Blue Notebook', URL), 'Pink | Blue Notebook')

    def test_variant_prices_remain_unknown_and_credentialed_image_is_rejected(self):
        p = product_page(product_data=[{'name': 'Notebook',
            'image': ['https://user:secret@fixture.org/private.png'],
            'offers': [{'price': '10', 'priceCurrency': 'USD'},
                       {'price': '12', 'priceCurrency': 'USD'}]}])
        row = research.product_observations([p])[0]
        self.assertEqual(row['public_price'], 'Unknown')
        self.assertEqual(row['currency'], 'Unknown')
        self.assertEqual(row['product_image_url'], 'Unknown')

    def test_product_focus_fetches_linked_products_and_preserves_markdown_image(self):
        product = URL + 'products/floral-grid-notebook'
        transport = SyntheticTransport(fetch_result(page(links=[{'url': product, 'text': 'Floral Grid Notebook'}])),
            fetch_result(page('/products/floral-grid-notebook', title='Floral Grid Notebook',
                text='![Floral Grid Notebook](https://cdn.shopify.com/s/files/floral-grid-notebook.webp)\nPrice: USD 12.50')))
        with patch.dict('os.environ', {'TINYFISH_API_KEY': KEY}, clear=True), \
                patch.object(tinyfish_client, 'build_opener', return_value=transport):
            capture = research.tinyfish_capture(URL, product_focus=True, max_pages=8)
        self.assertEqual(capture['status'], 'completed')
        self.assertEqual(len(transport.requests), 2)
        row = research.product_observations(capture['pages'], capture['acquisition'])[0]
        self.assertEqual(row['product_image_url'], 'https://cdn.shopify.com/s/files/floral-grid-notebook.webp')
        self.assertEqual(row['public_price'], '12.50')
        self.assertEqual(row['acquisition'], 'tinyfish_api_fetch')

    def test_product_focus_preserves_documented_description_and_image_fields(self):
        product = page('/products/floral-grid-notebook', title='Floral Grid Notebook', text='Price: USD 12.50')
        product['description'] = 'Floral cover with grid paper'
        product['image_links'] = ['https://cdn.shopify.com/floral-grid-notebook.webp']
        transport = SyntheticTransport(fetch_result(page(links=[{'url': product['url'], 'text': 'Notebook'}])),
                                       fetch_result(product))
        with patch.dict('os.environ', {'TINYFISH_API_KEY': KEY}, clear=True), \
                patch.object(tinyfish_client, 'build_opener', return_value=transport):
            capture = research.tinyfish_capture(URL, product_focus=True)
        row = research.product_observations(capture['pages'])[0]
        self.assertEqual((row['public_price'], row['currency']), ('12.50', 'USD'))
        self.assertEqual(row['product_image_url'], 'https://cdn.shopify.com/floral-grid-notebook.webp')
        self.assertEqual(row['observed_style_terms'], ['floral', 'grid'])

    def test_explicit_product_url_cannot_authorize_an_unlinked_external_shop(self):
        transport = SyntheticTransport(fetch_result(page()))
        with patch.dict('os.environ', {'TINYFISH_API_KEY': KEY}, clear=True), \
                patch.object(tinyfish_client, 'build_opener', return_value=transport):
            with self.assertRaisesRegex(ValueError, 'official or linked'):
                research.tinyfish_capture(URL, product_focus=True,
                    product_urls=['https://unlinked-fixture.org/products/notebook'])
        self.assertEqual(len(transport.requests), 1)

    def test_official_homepage_shop_link_allows_bounded_product_discovery_hop(self):
        shop = 'https://retailer-fixture-shop.org/'
        product = shop + 'products/illustrated-notebook'
        transport = SyntheticTransport(
            fetch_result(page(links=[{'url': shop, 'text': 'Shop'}])),
            fetch_result({'url': shop, 'title': 'Shop', 'text': 'Official linked shop',
                          'links': [{'url': product, 'text': 'Illustrated Notebook'}]}),
            fetch_result({'url': product, 'title': 'Illustrated Notebook', 'text': '$8', 'links': []}))
        with patch.dict('os.environ', {'TINYFISH_API_KEY': KEY}, clear=True), \
                patch.object(tinyfish_client, 'build_opener', return_value=transport):
            capture = research.tinyfish_capture(URL, product_focus=True, max_pages=8)
        self.assertEqual(capture['status'], 'completed')
        self.assertEqual(len(transport.requests), 3)
        row = research.product_observations(capture['pages'])[0]
        self.assertEqual(row['source_url'], product)
        self.assertEqual(row['observed_style_terms'], ['illustrated'])
        self.assertEqual(row['public_price'], 'Unknown')


if __name__ == '__main__':
    unittest.main()
