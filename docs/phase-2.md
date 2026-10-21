# Phase 2: Catalogue

## What this phase built

The storefront: the catalogue models and sample data, a full home page, the
catalogue listing with search, filters, sort and pagination, and the product
page with a size and thickness picker that updates price and stock. Everything
shows only active products and active variants, prices use Nepali grouping, and
the pages work without JavaScript.

## New and changed files

### Models and data (`catalog`)
- `catalog/models.py` - `Category`, `Size`, `Product`, `ProductImage`, `ProductVariant` with the plan's constraints (size dimensions > 0, firmness 1-5, variant price > 0, stock >= 0, unique SKU, unique product+size+thickness, one primary image per product). `Category` also carries a `tagline` and two illustration colours so the home cards and layer illustrations are drawn from data. `Product` has small display helpers (`size_count`, `card_stock`) computed from the prefetched active variants.
- `catalog/admin.py` - Category and Size admin; Product admin with variant and image inlines.
- `catalog/migrations/0001_initial.py` - creates the catalogue tables.
- `fixtures/catalog.json` - sample data: 4 categories, 4 sizes, 6 AARAM mattresses, and 48 variants (every product in Single/Double/Queen/King and 6 in/8 in), with a spread of stock so "In stock", "Few left" and "Out of stock" all appear. Load with `python manage.py loaddata fixtures/catalog.json`.

### Template filter
- `core/templatetags/core_extras.py` - the `npr` filter: Nepali grouping, e.g. `Rs. 1,25,000`.

### Views, URLs
- `catalog/views.py` - `catalogue` (search by name/material/category; filter by category, size, firmness bucket, price range and in-stock; sort; 12 per page; all state in the query string; efficient queries) and `product_detail` (active product and variants, the variant picker data, and the province delivery data).
- `catalog/urls.py` - `/mattresses/` and `/mattresses/<slug>/`, namespace `catalog`.
- `config/urls.py` - includes the catalogue at `/mattresses/`.
- `core/views.py` - the home page now feeds shop-by-feel, popular mattresses and the size guide from the database.

### Templates and styles
- `templates/partials/product_card.html` and `templates/partials/layer_illustration.html` - reusable product card and CSS layer illustration.
- `core/templates/core/home.html` - the full home page (hero, trust row, shop by feel, popular, size guide to scale, how ordering works).
- `catalog/templates/catalog/catalogue.html` - the listing with the filter form and pagination.
- `catalog/templates/catalog/product_detail.html` - the product page (illustration, size/thickness chips, price box, specs, delivery box).
- `static/js/variant-picker.js` - updates price, stock and the delivery estimate without a reload; the page already works without it.
- `static/css/main.css` - new sections for the home, cards, catalogue and product page.
- `templates/partials/header.html`, `footer.html` - nav and search now point at the catalogue.

### Tests
- `catalog/tests.py` - search, each filter, sort, inactive products hidden from the list and the detail page (404), the first in-stock variant chosen, and a query-count check proving no N+1.
- `core/tests.py` - the `npr` grouping unit tests.

## How to test it manually

1. `python manage.py migrate` then `python manage.py loaddata fixtures/catalog.json`.
2. `python manage.py runserver` and open the home page. Check the shop-by-feel cards, the popular mattresses, and the size guide drawn to scale.
3. Open **Mattresses**. Try the search ("latex"), tick Type and Size filters, set a price range, tick "In stock only", change the sort, and click Apply. The URL holds every choice, so you can reload or share it. Turn JavaScript off and it still works.
4. Open a mattress. Change the size and thickness and watch the price, SKU and stock update. With JavaScript off, pick a size and press "Show price for this size".
5. Change the province in the delivery box and watch the charge and days update.
6. In the admin, add a product with its variants and images as inline rows.

## Likely defense questions

1. **Why do price and stock live on `ProductVariant` and not on `Product`?**
   A mattress is sold in several sizes and thicknesses, and each has its own
   price and stock. Putting them on the variant lets the page show the exact
   price and availability for the chosen size, and lets stock be tracked per
   size.

2. **How does the catalogue keep its filters when you reload or share the link?**
   The filter form submits with GET, so every choice is in the URL query
   string. The view reads those parameters, and the template re-checks the
   boxes and re-selects the sort from them. Nothing is stored in the session,
   so the page is bookmarkable and works without JavaScript.

3. **How do you avoid running a database query for every product on the page?**
   The listing uses `select_related("category")` for the one-to-one side and
   `prefetch_related` for the variants, and annotates the lowest price in the
   query. A test counts the queries to make sure the number does not grow with
   the number of products.

4. **What stops an inactive (hidden) product from showing?**
   Both views filter `is_active=True`. The listing never includes inactive
   products, and the product page uses `get_object_or_404(..., is_active=True)`,
   so a hidden product's URL returns 404.

5. **Why does the product page still work without JavaScript?**
   The size and thickness picker is a real form. Without JavaScript it submits
   `?size=&thickness=` and the server renders the chosen variant's price and
   stock. The script only updates the page in place to avoid a reload; it is an
   enhancement, not a requirement.

## Tests in this phase

- `npr` formats 500, 1,500, 29,500, 1,25,000 and 12,50,000 correctly.
- Search finds products by name, material and category.
- Each filter works: category, size, firmness bucket, price range, in-stock.
- Sort by price orders by the lowest variant price.
- Inactive products are hidden from the listing and return 404 on the detail page.
- The first in-stock variant is selected on the product page.
- The catalogue runs a small, fixed number of queries regardless of product count.
