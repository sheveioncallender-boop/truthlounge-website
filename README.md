# Truth Lounge — Odoo 19 Community

Two independently installable apps, using the supplied Truth Lounge & Restaurant artwork:

| App | Technical folder | Responsibility |
| --- | --- | --- |
| Truth Website | `truth_lounge` | Homepage, branding, native shop links, reservations and gallery |
| Truth Kitchen Display | `truth_kitchen_display` | Display configuration, kitchen/bar screens and preparation history |

Neither app depends on the other. Kitchen display requires native Restaurant POS and Sales; website requires native Website eCommerce and Website Events. No Enterprise preparation module is required.

## Upgrade an existing combined installation on Cloudpepper

1. Take a database backup and deploy this revision of the repository. Keep the repository root on the addons path.
2. Restart/rebuild Odoo, then update the Apps list in developer mode.
3. **Install Truth Kitchen Display first.** Its installation transfers ownership of the existing preparation model, fields, access groups, views and constraints. Ticket IDs, stages, revisions and history remain in place. Previously enabled registers are selected on the initial display.
4. **Upgrade Truth Website**, which is the existing `truth_lounge` module under its new display name. Do not uninstall the original combined module. A migration guard blocks upgrading it first, because that could delete preparation metadata.
5. Reload the browser. The apps are now **Truth Website** and **Truth Kitchen Display**.
6. Open **Truth Kitchen Display → Displays**, open a configuration, choose its POS registers and station, save, then click **Open Display**.
7. Open the website root `/`. A single-website database automatically receives the Truth homepage, uploaded artwork as its logo, navigation and social links. The one-time repair also runs on upgrade. For a database with multiple websites, select the intended site under **Truth Website → Website Branding** and click **Apply Truth branding and navigation**.

Do not run a blanket upgrade before installing the new kitchen module. Complete both steps before resuming service. Existing native POS/Sales/Inventory applications remain installed; the split does not uninstall them.

## Fresh installation

Install either or both apps from Apps. The website activates automatically when the database has one website. The kitchen app creates an initial screen with no registers selected; configure it before service.

## Kitchen display configuration

Clicking **Truth Kitchen Display** opens **Displays**, not the live board. Each configuration has an **Open Display** button. A running display also has **Displays** and **Configuration** links.

Available settings:

- Name, company, one or more POS registers, Kitchen/Bar/both, and optional POS category filters.
- Optional confirmed website orders, using the native eCommerce app when installed. This includes websites in the selected company and does not require Truth Website.
- Refresh interval, late-item highlighting, closed-item retention and product images.
- Sound availability, initial volume and repeat interval. Set repeat to zero for new/amended-item alerts only. Browsers require **Enable sound** once per opened screen.
- Labels for the five stages: New → Acknowledged → Preparing → Ready → Completed. Labels are customizable; the progression is fixed.

Set **Truth preparation station** on each food/drink product to Kitchen or Bar. Leave it empty for fees and items that need no preparation. The old register checkbox is retained internally for migration; register selection on the display is now the setting used for polling.

Screens showing the same item share preparation progress. Kitchen and bar items can advance independently. Tickets are identified by source order, source line and station, so repeated polling does not duplicate them. Amendments reopen the affected item with an update warning; the quantity is the new total, not an instruction to remake the entire total.

The display reads server-saved POS orders from the last 48 hours and source orders for open preparation items. Offline/unsynchronized edits appear after Odoo syncs. Selecting an existing register may show recent historical orders; review the queue before service. Website orders enter only after native sale confirmation. Old `/truth/kitchen` bookmarks now open the display list; live boards use `/truth/kitchen/<display_id>`.

Grant staff **Preparation Display User** for operation or **Kitchen Display Manager** for configuration and preparation dismissal. Assign their ordinary native POS/Sales roles separately as appropriate. Administrator access is supported. Records are restricted by company. Dismissing preparation requires a reason and does not cancel/refund the native order.

## Website configuration

- The native Odoo header, mobile navigation, account menu, cart, shop, checkout and events remain in use. Truth colours and contact text are applied to the native header; default placeholder contact content is removed for branded sites.
- Homepage `/truth` is selected using Odoo's `homepage_url`; no replacement root controller or checkout flow is installed. Open Website uses `/` so Odoo performs its normal website selection.
- The supplied square brand artwork is used intact in the native logo field and website imagery. It is not a newly drawn substitute. Upload a different official logo through native Website settings if needed.
- Add the verified phone number, opening hours and address under **Website Branding**. No phone number, menu, price, event date or opening hour is invented.
- Add and publish actual products in native eCommerce. Featured products on the homepage no longer depend on preparation routing or installation of the kitchen app.
- Publish events in native Events. Paid event checkout requires native event-sale modules and a configured payment provider.
- Upload approved photos under **Truth Website → Website Gallery**. Until photos are published, Gallery links to the social pages.
- Reservation/private-event requests are under **Truth Website → Reservations & Private Events**. Staff must review availability and contact guests; there are no automatic table allocations, deposits or confirmation emails. Guest times use Trinidad & Tobago time and are stored in UTC.
- Assign **Truth Website Manager** for reservations/gallery. Existing Truth managers receive this role during migration. Website editor access is configured separately using native Odoo permissions.
- Setup does not change company identity, payment providers, tax rules, inventory, existing products or orders. Subsequent ordinary upgrades do not reset the logo/navigation after the one-time version-2 activation. The explicit branding button reapplies the supplied defaults.

## Native Odoo flow

There are no POS create/write/sync hooks, POS frontend patches, checkout overrides, sales-confirmation overrides, or payment/accounting/stock lifecycle changes. The display polls source records and writes only preparation tickets. Website orders remain native sales orders; they are not copied into POS. Tables, sessions, receipts, payments, refunds, invoicing and inventory continue through Odoo's existing flows.

## Verification

Run the local checks:

```bash
python checks/check_preparation.py
python checks/check_migration.py
python checks/check_structure.py
node --check truth_kitchen_display/static/src/js/kitchen.js
```

These cover preparation idempotency/amendments/removals, metadata ownership transfer and ticket identity, module independence, XML/manifest references, Python syntax and JavaScript syntax. The migration fixture executes the hook's SQL against a small SQLite metadata fixture, not a live Odoo database.

Odoo integration tests are included under `truth_kitchen_display/tests`. On a disposable Odoo 19 Community database:

```bash
odoo -d truth_test --addons-path=/path/to/odoo/addons,/path/to/this/repo -i truth_kitchen_display,truth_lounge --test-enable --test-tags /truth_kitchen_display --stop-after-init
```

This workspace has no runnable Odoo/PostgreSQL instance. Actual installation, migration, QWeb rendering and full POS/payment workflows have not been validated live. On a staging copy, follow the upgrade order above and check:

1. Existing preparation IDs/stages/history and staff access survive the split.
2. Kitchen app opens configuration; each screen filters the selected company/register/categories/station.
3. Root website shows the branded homepage and uploaded logo, with native mobile header/cart/checkout.
4. Normal POS edits/cancellation, confirmed website sales, preparation amendments and concurrent screens behave correctly.
5. Preparation advancement/dismissal does not change financial or stock records.

Cloudpepper deployment remains with the site owner.

Code: LGPL-3. Supplied artwork remains with its owner.
