# Truth Lounge & Restaurant — Odoo 19 Community

First implementation of the Truth website and preparation display by Spxcorp Limited.

## Native Odoo flow is preserved

This add-on does not override POS create/write/sync, checkout, payment processing, sales confirmation, invoicing, refunds, transfers, or stock valuation. It does not replace Odoo's native website header, account menu, cart, shop, checkout, event pages, or restaurant POS.

- Food & Drinks opens Odoo's native `/shop`. Products, variants, prices, pricelists, taxes, categories, publication and images remain standard Odoo records.
- What's On opens Odoo's native `/event`. Add and publish real events in Odoo Events. Ticket sales require Odoo's native event e-commerce modules and a configured provider.
- Website orders remain native sales orders. They are never converted into duplicate POS orders.
- Restaurant orders remain native POS orders. Existing tables, sessions, cashier payment methods and fiscal positions stay intact.
- Kitchen and bar preparation records are a separate display-only mirror. Advancing or dismissing an item cannot confirm/cancel/refund the source order, record a payment, invoice a customer, or move inventory.
- Odoo decides when a website sale is confirmed under its configured payment and manual-confirmation rules. The display observes that state; it does not change it or treat a browser return URL as payment proof.

## Included

- Responsive black/gold/ivory website using the supplied Truth brand artwork.
- Home, Our Story, Private Events, Gallery, Visit/Contact, and Reservation Request pages.
- Native shop, cart, checkout, customer portal and event listing, with scoped Truth button/header colours.
- Staff-managed reservation and private-event requests. No automatic table allocation or capacity assumptions.
- Staff-managed gallery photos, scoped to the selected website.
- Combined, Kitchen-only and Bar-only display views at `/truth/kitchen`.
- Stages: New → Acknowledged → Preparing → Ready → Completed.
- Separate progress for food/drinks; product images, notes, quantity amendments, elapsed time and late-item highlighting.
- New/amended order sounds, repeat alerts, volume/mute/test controls and full-screen mode.
- Audit history, manager-only preparation dismissal with a reason, company rules and stale-screen protection.

## Installation on Cloudpepper

1. Connect this repository using the branch you deploy (`main`, or `rebuild` when provided).
2. Ensure the repository root is on the add-ons path: it contains the `truth_lounge` module folder.
3. Rebuild/restart the Odoo 19 Community instance. Update the Apps list and install **Truth Lounge — Restaurant Experience**.
4. Dependencies use standard Community modules: Website eCommerce, Website Events, Restaurant POS, Sales/Stock, Purchases/Stock and Discuss. No Enterprise preparation-display dependency is used.
5. As an administrator, open **Truth Lounge → Website Branding**, select the intended website and click **Apply Truth branding and navigation**.
6. This activation sets that website's name, logo, social links and homepage `/truth`, then adds missing navigation entries. It leaves company details and existing products/orders unchanged. Review existing navigation in the native website editor if this is not a fresh website.
7. Enter the verified contact number and opening hours on the same website form. They are deliberately blank initially. Confirm the address before launch.
8. Grant staff **Truth Lounge → Preparation Display User**, or **Truth Manager** for reservations/gallery/dismissals. Grant their ordinary Odoo POS, Sales, Website or Events access separately as required.

## Kitchen and bar setup

1. In each relevant POS configuration, enable **Enable Truth kitchen/bar display**.
2. On each food/drink product, set **Truth preparation station** to Kitchen or Bar. Leave this blank for event tickets, fees and other items that do not require preparation.
3. Open `/truth/kitchen` while signed in. Choose the station for that device, then click **Enable sound**. Browsers require this interaction for audio.
4. Staff continue using their existing native POS workflow. Like the Ohana display, polling reads the server-saved order snapshot; unsynchronised/offline edits cannot appear until Odoo syncs them. There is no new Send button or POS frontend patch.
5. Polling is every five seconds. Recent native orders (last 48 hours) plus all source orders of open preparation items are checked. Enabling the display on an existing POS can therefore show recent orders; test activation timing before opening service.
6. A preparation item is identified by source order, source line and station. Repeated polling updates the same ticket. Food and drinks advance independently.
7. Quantity/product/note amendments resurface the affected item as **Updated order — check changes**. The displayed quantity is the latest total, not an instruction to remake the whole total. Kitchen staff should check what has already been prepared.
8. Dismissal closes preparation work only. Any sale/POS cancellation, customer credit or refund must still be processed through the existing Odoo workflow.
9. The display needs a network connection. When disconnected, it keeps the last displayed snapshot and clearly shows a connection warning. Standard Odoo POS offline operation is unaffected.

## Website launch setup

- Add actual menu items with prices, images and categories in native Odoo; publish approved products. No invented menu/prices, tax rates, hours, phone numbers or event dates are installed.
- Configure delivery/pickup, payment provider(s), order confirmation, tax and stock rules using native Odoo. This module does not guess or change those settings.
- The home page draws featured products from published, preparation-routed products. Until products are published, the product section is omitted and the menu button still opens the native shop.
- Publish real events through Odoo Events. Install/configure the standard event ticket checkout modules if paid entry is needed.
- Upload actual approved venue/food photos under **Truth Lounge → Website Gallery**. Until photos are published, Gallery links visitors to Truth's social pages.
- Reservation requests are stored under **Truth Lounge → Reservations & Private Events**. Staff must monitor this screen and contact guests. This release does not automatically send booking-confirmation emails, accept deposits or allocate POS tables.
- Reservations are entered in Trinidad & Tobago time and stored in UTC. Set staff user time zones appropriately.
- Inventory and purchasing use native Odoo. Ingredient recipes, portions, bottle measurements, warehouses, opening balances and replenishment rules need the business's actual data and configuration. No automatic ingredient consumption logic is included.
- The supplied square brand artwork is used intact. A clean transparent logo and real venue photography can improve the header and imagery later without changing the operating system.

## Validation and deployment status

Local checks cover Python syntax, XML parsing, manifest/file references, Odoo 19 inherited-view targets, JS syntax, native-flow isolation, and a runnable isolated preparation-mirroring test. Odoo integration tests are included under `truth_lounge/tests` for idempotency, independent stations, amendments, stale screens and access control.

This workspace has no runnable Odoo/PostgreSQL instance. Installation, actual QWeb rendering, browser layout and end-to-end POS/payment workflows must be verified on the target Odoo 19 Community test instance before production use. The code is not represented as production-validated or already deployed.

Suggested staging test:

1. Install the add-on and apply branding to the intended website. Check mobile/desktop header, native cart and checkout.
2. Send a normal dine-in POS order with food and drinks through the existing workflow; check independent display progress, edits and cancellation.
3. Complete a native website checkout in the provider's test mode. Verify one native sale, correct payment/accounting/stock behavior, and preparation only after confirmation.
4. Verify reservations, gallery publication, station routing and restricted access with real staff roles.
5. Verify refunds in native Odoo; preparation dismissal must not generate financial changes.

For automated Odoo integration tests on a disposable test database:

```bash
odoo -d truth_test --addons-path=/path/to/odoo/addons,/path/to/this/repo -i truth_lounge --test-enable --test-tags /truth_lounge --stop-after-init
```

## Provenance

Visual source: user-supplied Truth Lounge & Restaurant artwork and confirmed public social/location references.
Preparation architecture: the existing Ohana/Fuze project approach, with independent source polling and Truth-specific presentation. No other restaurant's branding, contacts, menus, prices or customer data is copied.

License: LGPL-3 for code; supplied brand artwork remains with its owner.
