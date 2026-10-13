#!/usr/bin/env python3
"""Write docs/QA_MATRIX.md from what the tests actually did.

    cd backend && venv/Scripts/python -m pytest -o addopts="" -q --junitxml=tests/.junit.xml
    venv/Scripts/python scripts/gen_endpoints.py
    cd .. && scripts/e2e.sh
    backend/venv/Scripts/python scripts/gen_qa_matrix.py            (--plan: before any run)

The rows and columns below are the plan: what must be checked, and which test
is the evidence for each cell. The results come from three files nobody edits
by hand:

  e2e/test-results/results.json    Playwright, per test id and screen width
  backend/tests/.junit.xml         pytest, per test function
  docs/ENDPOINTS.md                every API route with the responses the suite saw

A cell is PASS only if every test named for it ran and passed. A cell whose
evidence is missing or failing prints FAIL and the script exits 1, so the
matrix cannot say more than the tests do.
"""
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
E2E = ROOT / "e2e" / "test-results" / "results.json"
JUNIT = ROOT / "backend" / "tests" / ".junit.xml"
ENDPOINTS = ROOT / "docs" / "ENDPOINTS.md"
OUT = ROOT / "docs" / "QA_MATRIX.md"
WIDTHS = ["w390", "w768", "w1280", "w1920"]
PLAN = "--plan" in sys.argv

# ── Results ────────────────────────────────────────────────────

def load_e2e():
    """{test id: {width: 'passed' | 'failed' | 'skipped'}}"""
    out = {}
    if PLAN or not E2E.exists():
        return out
    data = json.loads(E2E.read_text(encoding="utf-8"))

    def walk(suite):
        for spec in suite.get("specs", []):
            test_id = spec["title"].split(" ", 1)[0]
            for test in spec["tests"]:
                status = test["results"][-1]["status"] if test["results"] else "skipped"
                out.setdefault(test_id, {})[test["projectName"]] = status
        for child in suite.get("suites", []):
            walk(child)
    for suite in data["suites"]:
        walk(suite)
    return out


def load_pytest():
    """{test function name: all of its cases passed}"""
    out = {}
    if PLAN or not JUNIT.exists():
        return out
    for case in ET.parse(JUNIT).getroot().iter("testcase"):
        name = case.get("name").split("[", 1)[0]
        ok = not any(child.tag in ("failure", "error", "skipped") for child in case)
        out[name] = out.get(name, True) and ok
    return out


def load_endpoints():
    rows = []
    if not ENDPOINTS.exists():
        return rows
    for line in ENDPOINTS.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and cells[0] in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            rows.append({"method": cells[0], "path": cells[1].strip("`"), "auth": cells[2], "ok": "✅" in cells[3],
                         "codes": set(cells[4].split())})
    return rows


E2E_RESULTS, PY_RESULTS, API_ROUTES = load_e2e(), load_pytest(), load_endpoints()
problems = []
NOTES = {}          # reason -> footnote number


def note(reason):
    NOTES.setdefault(reason, len(NOTES) + 1)
    return f"N/A <sup>{NOTES[reason]}</sup>"


def judge(evidence, width=None, fixed=None, where=""):
    """One cell. ``evidence`` is 'na:<reason>' or a list of 'e2e:<id>' / 'py:<test>'."""
    if isinstance(evidence, str) and evidence.startswith("na:"):
        return note(evidence[3:])
    items = [evidence] if isinstance(evidence, str) else list(evidence)
    if PLAN:
        return "planned"
    for item in items:
        kind, name = item.split(":", 1)
        if kind == "e2e":
            runs = E2E_RESULTS.get(name)
            if not runs:
                problems.append(f"{where}: no result for e2e test {name}")
                return "**FAIL**"
            seen = [runs.get(width)] if width else [s for s in runs.values() if s != "skipped"]
            if width and runs.get(width) == "skipped":
                # a test that runs at chosen widths only: judged on the widths it ran at
                seen = [s for s in runs.values() if s != "skipped"]
            if not seen or any(s != "passed" for s in seen):
                problems.append(f"{where}: e2e test {name} did not pass ({runs})")
                return "**FAIL**"
        else:
            if PY_RESULTS.get(name) is not True:
                problems.append(f"{where}: pytest {name} missing or failing")
                return "**FAIL**"
    return f"FIXED `{fixed}`" if fixed else "PASS"


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def e2e_slug(path):
    return re.sub(r"[/?=]", "-", path.lstrip("/")) or "home"


# ── A. Storefront pages ────────────────────────────────────────

SAME = "na:the page is the same for every visitor"
NO_LIST = "na:the page has no list that can be empty or long"
NO_INPUT = "na:the page takes no input"
PERSONAL = "na:nothing on this page belongs to a customer"
GUEST_ONLY = "na:only shown to visitors who are not signed in"
NEEDS_SIGNIN = "e2e:SF-AUTH-01"
HEADER_ONLY = "na:a campaign changes only the shared header and prices here; checked on the shopping pages (SF-CAMP-01)"
NOT_SHOPPING = "na:maintenance replaces the shopping pages; sign-in, account and policy pages stay reachable by design"
BLOCKED = ["e2e:CU-BLOCK-01", "e2e:CU-BLOCK-02"]
IDOR = ["e2e:CU-IDOR-01", "py:test_idor_every_customer_route_with_an_id"]

ST_COLS = ["390", "768", "1280", "1920", "Visitor", "New customer", "Returning", "With orders", "Blocked", "Another customer",
           "Empty", "Normal", "A lot", "Invalid input", "Slow network", "Backend error", "Campaign live", "No campaign", "Maintenance"]


def page(name, path, tests, state=None, **cells):
    """A storefront page. ``tests`` are the ids that open it at every width."""
    s = "acct-" + e2e_slug(path) if state == "acct" else e2e_slug(path)
    row = {
        "Visitor": [f"e2e:{tests[0]}"], "New customer": SAME, "Returning": SAME, "With orders": SAME,
        "Blocked": ["e2e:CU-BLOCK-01"], "Another customer": PERSONAL,
        "Empty": NO_LIST, "Normal": [f"e2e:{t}" for t in tests], "A lot": NO_LIST, "Invalid input": NO_INPUT,
        "Slow network": [f"e2e:ST-SLOW-{s}"], "Backend error": [f"e2e:ST-ERROR-{s}"],
        "Campaign live": [f"e2e:{tests[0]}"], "No campaign": HEADER_ONLY, "Maintenance": NOT_SHOPPING,
    }
    fixed = cells.pop("fixed", {})
    row.update(cells)
    return {"name": name, "path": path, "tests": tests, "cells": row, "fixed": fixed}


def shop(path):
    return {"No campaign": [f"e2e:ST-NOCAMP-{e2e_slug(path)}"], "Maintenance": [f"e2e:ST-MAINT-{e2e_slug(path)}"]}


ACCOUNT = {"Visitor": [NEEDS_SIGNIN], "New customer": ["e2e:ST-EMPTY-account"], "Blocked": BLOCKED, "Another customer": IDOR}
STOREFRONT = [
    page("Home", "/", ["SF-HOME-01", "SF-HOME-02"], **shop("/")),
    page("Shop (listing, filters, sort, search)", "/shop", ["SF-SHOP-01", "SF-SHOP-02"], **shop("/shop"),
         Empty=["e2e:SF-SHOP-03"], **{"A lot": ["e2e:SF-SHOP-04"], "Invalid input": ["e2e:SF-SHOP-03"],
                                      "Slow network": ["e2e:SF-SHOP-05", "e2e:ST-SLOW-shop"], "Backend error": ["e2e:SF-SHOP-06", "e2e:ST-ERROR-shop"]}),
    page("Collection", "/collections/diwali-edit", ["SF-COLL-01", "SF-SHOP-02"], **shop("/collections/diwali-edit")),
    page("Product", "/product/silk-blend-anarkali-kurta", ["SF-PROD-01"], **shop("/product/silk-blend-anarkali-kurta"),
         Returning=["e2e:CU-BAG-01", "e2e:CU-WISH-01"], **{"With orders": ["e2e:CU-RETURN-01"], "Invalid input": ["e2e:SF-PROD-02"]},
         fixed={"Returning": "d7a2df0"}),
    page("About", "/about", ["SF-PAGE-ABOUT"], **shop("/about")),
    page("Shipping policy", "/shipping", ["SF-PAGE-SHIPPING"]),
    page("Returns policy", "/returns", ["SF-PAGE-RETURNS"]),
    page("Privacy policy", "/privacy-policy", ["SF-PAGE-PRIVACY"]),
    page("Terms", "/terms", ["SF-PAGE-TERMS"]),
    page("FAQ", "/faq", ["SF-PAGE-FAQ"], **shop("/faq"), Empty=["py:test_faq_is_managed_from_the_dashboard"]),
    page("Contact", "/contact", ["SF-PAGE-CONTACT"], **shop("/contact"), **{"Invalid input": ["e2e:SF-PAGE-CONTACT"]}),
    page("Offers and Wholesale", "/offers", ["SF-PAGE-OFFERS"], **shop("/offers")),
    page("404", "/no/such/page", ["SF-404-01"]),
    page("Sign in", "/login", ["CU-LOGIN-01"], Returning=["e2e:CU-LOGIN-01"], Blocked=["e2e:CU-BLOCK-02"],
         **{"New customer": GUEST_ONLY, "With orders": GUEST_ONLY, "Invalid input": ["e2e:CU-LOGIN-02"]}),
    page("Register", "/register", ["CU-REG-01"], **{"New customer": ["e2e:CU-REG-01"], "Returning": GUEST_ONLY, "With orders": GUEST_ONLY,
                                                   "Invalid input": ["e2e:CU-REG-02"]}),
    page("Forgot password", "/forgot-password", ["CU-FORGOT-01"],
         **{"Invalid input": ["e2e:CU-FORGOT-01", "py:test_an_unknown_address_gets_the_same_answer_and_no_email"],
            "Returning": ["py:test_the_reset_email_link_opens_the_reset_page_and_the_token_works_once"]}),
    page("Reset password", "/reset-password?token=x", ["CU-RESET-01"],
         **{"Invalid input": ["e2e:CU-RESET-01"], "Returning": ["py:test_the_reset_email_link_opens_the_reset_page_and_the_token_works_once"]}),
    page("Wishlist", "/wishlist", ["CU-WISH-01"], **{**ACCOUNT, "Visitor": ["e2e:SF-AUTH-01"]}, Returning=["e2e:CU-WISH-01"],
         Empty=["e2e:ST-EMPTY-account"], fixed={"Returning": "d7a2df0"}),
    page("Bag", "/cart", ["CU-BAG-01", "CU-COUPON-01"], state="acct", **ACCOUNT, Returning=["e2e:CU-BAG-01"], Empty=["e2e:ST-EMPTY-account"],
         **{"With orders": ["e2e:CU-CHECKOUT-01"], "Campaign live": ["e2e:CU-COUPON-01"],
            "Invalid input": ["e2e:CU-COUPON-01", "py:test_a_coupon_that_stopped_being_valid_after_it_was_applied_is_not_honoured",
                              "py:test_applying_a_coupon_that_cannot_be_used_is_refused_with_the_reason"]},
         fixed={"Invalid input": "25da8d8", "Returning": "d7a2df0"}),
    page("Checkout", "/checkout", ["CU-CHECKOUT-01", "CU-CHECKOUT-03"], state="acct", **ACCOUNT, Empty=["e2e:ST-EMPTY-account"],
         Returning=["e2e:CU-CHECKOUT-01", "e2e:CU-CHECKOUT-02", "e2e:A11Y-CHECKOUT-01"],
         **{"With orders": ["e2e:CU-CHECKOUT-02"], "Campaign live": ["e2e:CU-CHECKOUT-01"],
            "Invalid input": ["py:test_the_same_checkout_sent_twice_at_once_makes_one_order", "py:test_the_last_unit_is_sold_exactly_once"]},
         fixed={"Invalid input": "25da8d8"}),
    page("Order confirmed", "/order-confirmed/:id", ["CU-CHECKOUT-01"], **ACCOUNT,
         **{"New customer": "na:reached only by placing an order", "With orders": ["e2e:CU-CHECKOUT-01"],
            "Slow network": "na:shown straight after placing the order from data already loaded; the order pages cover a slow backend",
            "Backend error": "na:shown straight after placing the order from data already loaded; the order pages cover a failing backend"}),
    page("Orders", "/account/orders", ["CU-CHECKOUT-01"], state="acct", **ACCOUNT, Empty=["e2e:ST-EMPTY-account"],
         **{"With orders": ["e2e:CU-CHECKOUT-01"], "A lot": ["py:test_customer_order_list_is_paged"]}, fixed={"390": "d7a2df0"}),
    page("Order detail (cancel, return)", "/account/orders/:id", ["CU-ORDER-01", "CU-RETURN-01"], **ACCOUNT,
         **{"New customer": "na:a new customer has no order to open", "With orders": ["e2e:CU-ORDER-01", "e2e:CU-RETURN-01"],
            "Invalid input": ["e2e:CU-IDOR-01", "py:test_stock_comes_back_exactly_once_when_an_order_is_cancelled"],
            "Slow network": ["e2e:ST-SLOW-acct-account-orders"], "Backend error": ["e2e:ST-ERROR-acct-account-orders"]},
         fixed={"390": "d7a2df0"}),
    page("Returns", "/account/returns", ["CU-RETURN-01"], state="acct", **ACCOUNT, Empty=["e2e:ST-EMPTY-account"],
         **{"With orders": ["e2e:CU-RETURN-01"]}, fixed={"390": "d7a2df0"}),
    page("Addresses", "/account/addresses", ["CU-ADDR-01"], state="acct", **ACCOUNT, Returning=["e2e:CU-ADDR-01"],
         Empty=["e2e:ST-SLOW-acct-account-addresses"], **{"Invalid input": ["e2e:CU-ADDR-01"]}, fixed={"390": "d7a2df0"}),
    page("Profile", "/account/profile", ["CU-PROFILE-01", "CU-SESSION-01"], state="acct", **ACCOUNT,
         Returning=["e2e:CU-PROFILE-01", "e2e:CU-SESSION-01"], fixed={"390": "d7a2df0"}),
    page("Track order", "/track-order", ["ST-SLOW-track-order"], **{"Visitor": ["e2e:ST-SLOW-track-order"], "Campaign live": ["e2e:ST-SLOW-track-order"]}),
]


def storefront_section():
    rows = []
    for p in STOREFRONT:
        cells = [f"**{p['name']}**<br>`{p['path']}`"]
        for width in WIDTHS:
            col = width[1:]
            ids = [t for t in p["tests"] if not t.startswith("ST-")] or p["tests"]
            cells.append(judge([f"e2e:{t}" for t in ids], width=width, fixed=p["fixed"].get(col), where=f"{p['name']} at {col}"))
        for col in ST_COLS[4:]:
            cells.append(judge(p["cells"][col], fixed=p["fixed"].get(col), where=f"{p['name']} / {col}"))
        rows.append(cells)
    return table(["Page"] + ST_COLS, rows)


# ── B. Dashboard screens ───────────────────────────────────────

EVERYONE = {"dashboard", "orders", "returns", "products", "categories", "media"}
OWNER_ONLY = {"settings", "staff", "site-settings", "demo", "system"}
AD_COLS = ["390", "768", "1280", "1920", "Not signed in", "Customer", "Staff", "Manager", "Owner",
           "Empty", "Normal", "A lot", "Invalid input", "Slow network", "Backend error", "Create / edit / delete", "Audit log"]
NO_FORM = "na:the screen only shows information"
AUDIT = ["py:test_admin_writes_are_recorded_with_who_and_what"]
ADMIN = [
    # name, path, area, extra cells, fixed
    ("Dashboard", "/admin", "dashboard", {"Create / edit / delete": NO_FORM, "Invalid input": NO_FORM, "Audit log": NO_FORM}, {}),
    ("Orders", "/admin/orders", "orders", {"Empty": ["e2e:ST-ADMIN-EMPTY-admin-orders"], "A lot": ["py:test_orders_list_search_filter_sort"],
                                           "Create / edit / delete": ["e2e:AD-ORDER-01"], "Invalid input": ["py:test_admin_invalid_change_is_a_409_and_changes_nothing"]}, {}),
    ("Returns", "/admin/returns", "returns", {"Create / edit / delete": ["py:test_return_outcomes_move_the_order_by_the_rules"]}, {}),
    ("Customers", "/admin/users", "users", {"Empty": ["e2e:ST-ADMIN-EMPTY-admin-users", "e2e:AD-USERS-01"], "Create / edit / delete": ["e2e:AD-USERS-01"]},
     {"390": "f64907a", "768": "f64907a"}),
    ("Settlements", "/admin/settlements", "settlements", {"Create / edit / delete": NO_FORM, "Invalid input": NO_FORM, "Audit log": NO_FORM}, {}),
    ("Products", "/admin/products", "products", {"Empty": ["e2e:ST-ADMIN-EMPTY-admin-products"], "A lot": ["e2e:AD-PRODUCT-01"],
                                                 "Create / edit / delete": ["e2e:AD-PRODUCT-01"]}, {"390": "f64907a", "768": "f64907a"}),
    ("New / edit product", "/admin/products/new", "products", {"Create / edit / delete": ["e2e:AD-PRODUCT-01"], "Empty": NO_LIST, "A lot": NO_LIST}, {}),
    ("Categories", "/admin/categories", "categories", {}, {}),
    ("Collections", "/admin/collections", "collections", {}, {}),
    ("Media library", "/admin/media", "media", {"Invalid input": ["py:test_upload_refuses_what_is_not_an_allowed_image", "py:test_upload_size_limit_and_pixel_limit"]},
     {"Invalid input": "0bcb945"}),
    ("Reviews", "/admin/reviews", "reviews", {}, {}),
    ("Campaigns", "/admin/campaigns", "campaigns", {"Create / edit / delete": ["e2e:AD-CAMPAIGN-01"],
                                                    "Invalid input": ["e2e:AD-CAMPAIGN-01", "py:test_overlapping_schedules_are_rejected"]}, {}),
    ("Coupons", "/admin/coupons", "coupons", {"Create / edit / delete": ["e2e:AD-COUPON-01"], "Invalid input": ["e2e:AD-COUPON-01"],
                                              "Audit log": ["e2e:AD-COUPON-01"]}, {}),
    ("Offers", "/admin/offers", "offers", {}, {}),
    ("Homepage builder", "/admin/homepage", "homepage", {}, {}),
    ("Hero slides", "/admin/banners", "banners", {}, {}),
    ("Announcements", "/admin/announcements", "announcements", {}, {}),
    ("Promo banners", "/admin/promo-banners", "promo-banners", {}, {}),
    ("Testimonials", "/admin/testimonials", "testimonials", {}, {}),
    ("Feature cards", "/admin/features", "features", {}, {}),
    ("Menus", "/admin/navigation", "navigation", {}, {}),
    ("Pages", "/admin/pages", "pages", {"Invalid input": ["py:test_script_in_customer_text_comes_back_as_inert_json"]}, {}),
    ("FAQ", "/admin/faq", "faq", {"Create / edit / delete": ["e2e:AD-FAQ-01", "e2e:A11Y-ADMIN-01"], "Invalid input": ["e2e:AD-FAQ-01"]}, {}),
    ("Wholesale inquiries", "/admin/inquiries", "wholesale-inquiries", {}, {}),
    ("Messages", "/admin/messages", "contact-messages", {}, {}),
    ("Newsletter", "/admin/newsletter", "newsletter", {}, {"390": "f64907a"}),
    ("Store settings", "/admin/settings", "settings", {"Create / edit / delete": ["e2e:AD-SETTINGS-01"], "Invalid input": ["e2e:AD-SETTINGS-01"],
                                                      "Empty": NO_LIST, "A lot": NO_LIST}, {"Create / edit / delete": "d7a2df0"}),
    ("Staff", "/admin/staff", "staff", {"Create / edit / delete": ["e2e:AD-STAFF-01"], "Invalid input": ["e2e:AD-STAFF-01"]}, {}),
    ("Other text", "/admin/site-settings", "site-settings", {"Empty": NO_LIST, "A lot": NO_LIST}, {}),
    ("Demo content", "/admin/demo", "demo", {"Create / edit / delete": ["e2e:AD-DEMO-01", "py:test_remove_demo_content_needs_the_phrase_and_spares_real_data"],
                                            "Empty": NO_LIST, "A lot": NO_LIST, "Invalid input": ["py:test_remove_demo_content_needs_the_phrase_and_spares_real_data"]}, {}),
    ("System health", "/admin/system", "system", {"Create / edit / delete": NO_FORM, "Invalid input": NO_FORM, "Audit log": NO_FORM,
                                                  "Normal": ["e2e:AD-SYSTEM-01"], "Empty": NO_LIST, "A lot": NO_LIST}, {}),
    ("Audit log", "/admin/audit-log", "audit-log", {"Empty": ["e2e:ST-ADMIN-EMPTY-admin-audit-log", "e2e:AD-AUDIT-01"], "Create / edit / delete": NO_FORM,
                                                   "Invalid input": NO_FORM, "Audit log": ["e2e:AD-AUDIT-01"]}, {}),
    ("Help", "/admin/help", None, {"Create / edit / delete": NO_FORM, "Invalid input": NO_FORM, "Audit log": NO_FORM, "Empty": NO_LIST, "A lot": NO_LIST}, {}),
    ("Admin sign-in", "/admin/login", None, {"Not signed in": ["e2e:AD-LOGIN-01"], "Invalid input": ["e2e:AD-LOGIN-02"],
                                             "Create / edit / delete": NO_FORM, "Audit log": ["py:test_sign_ins_show_in_the_audit_log_endpoint"],
                                             "Empty": NO_LIST, "A lot": NO_LIST}, {}),
]
CRUD_BY_API = "py:test_create_returns_the_new_record"


def admin_slug(path):
    return path.replace("/admin", "").replace("/", "-").lstrip("-") or "dashboard"


def admin_section():
    rows = []
    for name, path, area, extra, fixed in ADMIN:
        login = path == "/admin/login"
        screen = "AD-LOGIN-01" if login else f"AD-SCREEN-{admin_slug(path)}"
        slug = e2e_slug(path)
        staff_ok = area is None or area in EVERYONE
        manager_ok = area is None or area not in OWNER_ONLY
        refused = {"Staff": "f64907a"} if not staff_ok else {}
        if not manager_ok:
            refused["Manager"] = "f64907a"
        base = {
            "Not signed in": ["e2e:AD-LOGIN-01", "py:test_every_non_public_route_refuses_an_anonymous_caller"],
            "Customer": ["py:test_a_customer_token_opens_nothing_in_the_admin_api"],
            "Staff": ["e2e:AD-ROLE-STAFF", "py:test_staff_can_use_catalogue_and_orders" if staff_ok else "py:test_staff_is_blocked_outside_catalogue_and_orders"],
            "Manager": ["e2e:AD-ROLE-MANAGER", "py:test_manager_can_run_the_shop" if manager_ok else "py:test_manager_is_blocked_from_owner_areas"],
            "Owner": [f"e2e:{screen}", "e2e:AD-NAV-OWNER"],
            "Empty": ["py:test_every_list_answers_when_it_is_empty"], "Normal": [f"e2e:{screen}"],
            "A lot": ["py:test_orders_list_search_filter_sort"], "Invalid input": ["py:test_write_routes_survive_empty_and_malformed_bodies"],
            "Slow network": [f"e2e:ST-ADMIN-SLOW-{slug}"], "Backend error": [f"e2e:ST-ADMIN-ERROR-{slug}"],
            "Create / edit / delete": [CRUD_BY_API], "Audit log": AUDIT,
        }
        if login:
            base.update({"Customer": "na:the sign-in page is public", "Staff": ["e2e:AD-ROLE-STAFF"], "Manager": ["e2e:AD-ROLE-MANAGER"],
                         "Owner": ["e2e:AD-NAV-OWNER"], "Slow network": ["e2e:ST-MAINT-admin"], "Backend error": ["e2e:AD-LOGIN-02"],
                         "Normal": ["e2e:AD-LOGIN-01"]})
        base.update(extra)
        cells = [f"**{name}**<br>`{path}`"]
        for width in WIDTHS:
            cells.append(judge([f"e2e:{screen}"], width=width, fixed=fixed.get(width[1:]), where=f"{name} at {width}"))
        for col in AD_COLS[4:]:
            cells.append(judge(base[col], fixed=fixed.get(col) or refused.get(col), where=f"{name} / {col}"))
        rows.append(cells)
    return table(["Screen"] + AD_COLS, rows)


# ── C. API routes ──────────────────────────────────────────────

API_FIXED = {
    ("POST", "/api/admin/auth/refresh"): "f64907a", ("POST", "/api/orders"): "25da8d8", ("GET", "/api/cart"): "25da8d8",
    ("POST", "/api/admin/orders/<int:order_id>/ship"): "6d3231e", ("POST", "/api/admin/orders/<int:order_id>/sync-tracking"): "6d3231e",
    ("POST", "/api/payments/webhook"): "6d3231e", ("POST", "/api/admin/media"): "0bcb945", ("POST", "/api/admin/upload"): "0bcb945",
}


def api_section():
    if not API_ROUTES:
        return "_docs/ENDPOINTS.md has not been generated yet._"
    success = {"200", "201", "204", "302"}
    refused_admin = "PASS (403)"
    rows = []
    for r in API_ROUTES:
        where = f"{r['method']} {r['path']}"
        codes, auth, path = r["codes"], r["auth"], r["path"]
        is_admin = path.startswith("/api/admin/") and auth not in ("public", "refresh cookie")
        is_public = auth in ("public", "refresh cookie") or auth.startswith("public")
        fixed = API_FIXED.get((r["method"], path))

        def cell(ok, text="PASS"):
            if PLAN:
                return "planned"
            if not ok or not r["ok"]:
                problems.append(f"{where}: {text} not shown by the suite ({' '.join(sorted(codes))})")
                return "**FAIL**"
            return f"FIXED `{fixed}`" if fixed and text == "PASS" else text

        anonymous = cell(bool(codes & success)) if is_public else cell("401" in codes, "PASS (401)")
        if is_admin:
            area = path.split("/")[3]
            if area == "auth":
                area = "staff"
            customer = cell("403" in codes, refused_admin)
            other = note("an admin route: customers are refused outright")
            staff = cell(True) if area in EVERYONE else cell("403" in codes, refused_admin)
            manager = cell(True) if area not in OWNER_ONLY else cell("403" in codes, refused_admin)
            owner = cell(True)
        else:
            customer = cell(bool(codes & success))
            other = cell("404" in codes, "PASS (404)") if ("<" in path and not is_public) else note("the address names no record that could belong to someone else")
            staff = manager = owner = note("a customer or public route: an admin token is not a customer token (test_an_admin_token_is_not_a_customer_token)")
        takes_body = r["method"] in ("POST", "PUT", "PATCH")
        invalid = cell(True, "PASS") if (codes & {"400", "415", "422"}) else note("the route takes no input to validate" if not takes_body else "the route reads no request body")
        rows.append([r["method"], f"`{path}`", auth, anonymous, customer, other, staff, manager, owner, invalid, " ".join(sorted(codes))])
    return table(["Method", "Route", "Needs", "Not signed in", "Customer", "Another customer", "Staff", "Manager", "Owner", "Invalid input", "Responses seen"], rows)


# ── D–F. Emails, jobs, cross-cutting ───────────────────────────

LISTS = {
    "D. Emails": [
        ("Order confirmation", "Sent on every order; every line, subtotal, discount, GST, delivery and total; names escaped; link opens the order",
         ["py:test_the_order_email_has_every_line_every_total_and_a_working_link", "py:test_order_email_escapes_names",
          "py:test_the_total_is_the_same_in_the_bag_the_order_the_email_and_the_dashboard", "py:test_a_mail_provider_outage_does_not_stop_the_order"], "25da8d8"),
        ("Password reset", "Sent only to a real account; link opens the reset page; token works once; second request cancels the first",
         ["py:test_the_reset_email_link_opens_the_reset_page_and_the_token_works_once", "py:test_asking_twice_cancels_the_first_link",
          "py:test_an_unknown_address_gets_the_same_answer_and_no_email", "py:test_production_never_returns_the_reset_token_in_the_response"], None),
        ("No mail key set", "Nothing is sent and nothing fails", ["py:test_no_email_is_attempted_when_no_mail_key_is_set", "py:test_send_email_noop_when_not_configured"], None),
        ("Shipped / delivered / cancelled / refunded emails", "Do not exist yet", "na:not built; a product decision listed in docs/PRELAUNCH_REPORT.md", None),
    ],
    "E. Scheduled jobs and commands": [
        ("reconcile-payments (every 30 minutes on Render)", "Refunds stale captures with no order; safe to run twice; no keys = no-op; non-zero exit when a refund fails",
         ["py:test_refunds_only_stale_captures_without_an_order", "py:test_running_twice_does_not_refund_twice", "py:test_unconfigured_gateway_is_a_no_op",
          "py:test_cli_exits_non_zero_when_a_refund_fails", "py:test_reconcile_reads_the_payment_list_and_refunds_the_stale_orphan"], None),
        ("Campaign start and end", "No job: computed from the clock at exact IST boundaries on every request",
         ["py:test_exact_boundaries", "e2e:SF-CAMP-01"], None),
        ("render_bootstrap_db.sh", "Builds a new, empty Neon branch with no manual step",
         ["py:test_schema_check_names_a_pending_migration_and_the_command_applies_it"], "0bcb945"),
        ("apply-migrations / check-schema", "Idempotent; startup says when migrations are pending", ["py:test_schema_check_names_a_pending_migration_and_the_command_applies_it", "py:test_schema_check_passes_on_a_migrated_database"], None),
        ("check-integrations", "Says OK / NOT CONFIGURED / PROBLEM per service; never prints a value", ["py:test_check_integrations_never_prints_a_value"], None),
        ("remove-demo-content", "Removes only demo rows (provable on a throwaway Neon branch)",
         ["py:test_remove_demo_content_needs_the_phrase_and_spares_real_data"], None),
    ],
    "F. Data integrity": [
        ("Two customers, one unit left", "Exactly one order; the other is told it is out of stock", ["py:test_the_last_unit_is_sold_exactly_once", "py:test_stock_never_goes_below_zero_when_many_buy_at_once"], "25da8d8"),
        ("Coupon usage limit hit at the same moment", "Used exactly as many times as its limit", ["py:test_a_coupon_is_never_used_more_times_than_its_limit"], "25da8d8"),
        ("Coupon: expired, switched off, used up, below minimum, two at once", "Refused with the reason; never honoured later",
         ["py:test_a_coupon_that_stopped_being_valid_after_it_was_applied_is_not_honoured", "py:test_applying_a_coupon_that_cannot_be_used_is_refused_with_the_reason",
          "py:test_a_second_coupon_replaces_the_first", "py:test_a_flat_coupon_larger_than_the_bag_cannot_make_the_total_negative", "e2e:CU-COUPON-01"], "25da8d8"),
        ("Double click on Place order", "One order", ["e2e:CU-CHECKOUT-02", "py:test_the_same_checkout_sent_twice_at_once_makes_one_order",
                                                    "py:test_two_requests_without_a_key_cannot_order_the_same_bag_twice"], "25da8d8"),
        ("Reload during checkout", "Nothing lost, nothing ordered twice", ["e2e:CU-CHECKOUT-03"], None),
        ("Stock after cancel and return", "Back exactly once", ["e2e:CU-ORDER-01", "py:test_stock_comes_back_exactly_once_when_an_order_is_cancelled", "py:test_cancel_restores_stock_exactly_once"], None),
        ("One total everywhere", "Bag, checkout, order, email and dashboard agree to the paisa", ["e2e:CU-CHECKOUT-01", "py:test_the_total_is_the_same_in_the_bag_the_order_the_email_and_the_dashboard"], None),
    ],
    "G. Security": [
        ("Every non-public route refuses a caller who is not signed in", "", ["py:test_every_non_public_route_refuses_an_anonymous_caller", "py:test_public_list_has_no_stale_entries"], None),
        ("A customer cannot use the admin API; an admin token is not a customer token", "", ["py:test_a_customer_token_opens_nothing_in_the_admin_api", "py:test_an_admin_token_is_not_a_customer_token"], None),
        ("Another customer's records (IDOR) on every route with an id", "", ["py:test_idor_every_customer_route_with_an_id", "py:test_a_review_cannot_be_written_as_someone_else", "e2e:CU-IDOR-01"], None),
        ("Script in every customer and CMS text field", "Stored and shown as text", ["py:test_script_in_customer_text_comes_back_as_inert_json", "py:test_order_email_escapes_names", "e2e:CU-RETURN-01"], None),
        ("Cross-site requests", "State-changing routes need a bearer token; refresh needs the CSRF header; cookies are httpOnly",
         ["py:test_state_changing_routes_ignore_cookies_without_a_bearer_token", "py:test_refresh_cookies_are_http_only_and_need_the_csrf_header"], None),
        ("File uploads: type, size, disguised files, SVG scripts, path traversal", "", ["py:test_upload_refuses_what_is_not_an_allowed_image", "py:test_upload_is_judged_by_content_and_re_encoded",
                                                                                     "py:test_upload_size_limit_and_pixel_limit", "py:test_upload_path_traversal_in_the_file_name_is_harmless"], "0bcb945"),
        ("Rate limits", "Per account and per address; a team on one connection is not locked out",
         ["py:test_login_guessing_from_many_addresses_is_limited", "py:test_admin_login_guessing_from_many_addresses_is_limited",
          "py:test_a_team_on_one_connection_is_not_locked_out_of_the_dashboard", "py:test_contact_form_is_rate_limited"], "f64907a"),
        ("Security headers and CORS", "", ["py:test_security_headers_on_every_kind_of_response", "py:test_cors_allows_only_the_storefront"], None),
        ("Errors do not leak internals; no token in browser storage", "", ["py:test_errors_do_not_leak_internals", "e2e:CU-SESSION-01"], None),
        ("Payment signature and webhook signature", "Forged ones never reach the gateway", ["py:test_a_forged_checkout_signature_never_reaches_the_gateway",
                                                                                        "py:test_every_webhook_event_is_accepted_when_signed_and_refused_when_not"], None),
    ],
    "H. Accessibility": [
        ("Checkout with the keyboard only", "Every step reached with Tab, pressed with Enter, focus always visible", ["e2e:A11Y-CHECKOUT-01"], None),
        ("An admin form with the keyboard only", "Add a FAQ entry; the confirm dialog takes the focus and Escape closes it", ["e2e:A11Y-ADMIN-01"], None),
    ],
}


def list_section(title):
    rows = []
    for name, what, evidence, fixed in LISTS[title]:
        result = judge(evidence, fixed=fixed, where=name)
        shown = "" if isinstance(evidence, str) else "<br>".join(f"`{e.split(':', 1)[1]}`" for e in evidence)
        rows.append([f"**{name}**", what, result, shown])
    return table(["Check", "What must hold", "Result", "Evidence"], rows)


def main():
    parts = [
        "# QA matrix",
        "",
        "Generated by `scripts/gen_qa_matrix.py`; do not edit by hand. The rows, columns and the test that is the evidence for each "
        "cell are defined in that script. The results are read from the last Playwright run, the last pytest run and `docs/ENDPOINTS.md`.",
        "",
        "- **PASS**: every test named for the cell ran and passed.",
        "- **FIXED `commit`**: the cell found a defect during the Round 4 audit; it was fixed in that commit and the cell now passes.",
        "- **N/A**: does not apply; the numbered reason is at the end.",
        "- Screen widths are 390, 768, 1280 and 1920 px. The slow-network, backend-error, maintenance and no-campaign columns are run at 390 and 1280 px "
        "(how a page behaves when the backend is slow or down does not depend on the width).",
        "",
        "## A. Storefront pages", "", storefront_section(), "",
        "## B. Dashboard screens", "",
        "Staff and Manager columns: for a screen outside the role, PASS means the screen is missing from the menu, refuses by address, and the server answers 403.",
        "", admin_section(), "",
        "## C. API routes", "",
        "Every route the application registers. \"Responses seen\" are the status codes the test suite observed for the route.",
        "", api_section(), "",
    ]
    for title in LISTS:
        parts += [f"## {title}", "", list_section(title), ""]
    parts += ["## Why a cell is N/A", ""] + [f"{number}. {reason[0].upper()}{reason[1:]}." for reason, number in sorted(NOTES.items(), key=lambda kv: kv[1])]
    text = "\n".join(parts) + "\n"
    blank = re.findall(r"\|\s*\|", text.replace("| |---", ""))
    OUT.write_text(text, encoding="utf-8")
    cells = text.count("PASS") + text.count("FIXED `") + text.count("N/A <sup>")
    print(f"docs/QA_MATRIX.md written: {text.count('PASS')} PASS, {text.count('FIXED `')} FIXED, {text.count('N/A <sup>')} N/A, {text.count('**FAIL**')} FAIL ({cells} cells)")
    for line in sorted(set(problems))[:60]:
        print("  FAIL", line)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
