import os
import tempfile
from pathlib import Path

# Use a completely separate database so regression tests never touch user data.
TEST_DB = Path(tempfile.gettempdir()) / "village_market_v64_regression.db"
try:
    TEST_DB.unlink()
except FileNotFoundError:
    pass
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["ADMIN_ID"] = "admin"
os.environ["ADMIN_PASSWORD"] = "looser@123"

from fastapi.testclient import TestClient
from backend.database import Base, SessionLocal, engine
from backend import models  # register ORM tables for the isolated test database
Base.metadata.create_all(engine)
from backend.main import app
from backend.models import Booking, Crop

client = TestClient(app)


def headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def otp_login(phone: str, role: str, name: str):
    r = client.post("/api/auth/send-otp", json={"phone": phone})
    assert r.status_code == 200, r.text
    otp = r.json()["demo_otp"]
    assert len(otp) == 6 and otp.isdigit()
    r = client.post(
        "/api/auth/verify-otp",
        json={"phone": phone, "code": otp, "role": role, "name": name, "email": None},
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


def create_crop(farmer_token: str, name="Tomato", qty=100):
    data = {
        "name": name,
        "category": "Vegetables",
        "quantity_kg": str(qty),
        "location": "Survey 10, Farm Road",
        "address_line": "",
        "village": "Test Village",
        "mandal": "Test Mandal",
        "district": "Kadapa",
        "state": "Andhra Pradesh",
        "pincode": "516001",
        "landmark": "Near School",
        "latitude": "14.4673",
        "longitude": "78.8242",
        "expected_price": "20",
        "quality": "Grade A",
        "harvest_date": "2026-08-20",
        "details": "Regression test crop",
    }
    r = client.post("/api/crops", headers=headers(farmer_token), data=data, files={"photo": ("crop.jpg", b"fake-image-data", "image/jpeg")})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def approve_crop(admin_token: str, crop_id: int, price=25, qty=100):
    r = client.patch(
        f"/api/admin/crops/{crop_id}",
        headers=headers(admin_token),
        json={
            "action": "approve",
            "market_price": price,
            "inspected_quantity": qty,
            "inspected_quality": "Premium",
            "admin_note": "Verified",
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_complete_v63_v64_regression_flow():
    # Static pages
    assert client.get("/").status_code == 200
    assert client.get("/admin").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/admin.js").status_code == 200

    # WebSocket channel accepts live connections.
    with client.websocket_connect("/ws/admin") as ws:
        ws.send_text("ping")

    # Authentication and role separation
    farmer = otp_login("9000000001", "farmer", "Farmer One")
    buyer = otp_login("9000000002", "buyer", "Buyer One")
    buyer2 = otp_login("9000000003", "buyer", "Buyer Two")

    r = client.post("/api/admin/login", json={"admin_id": "admin", "password": "wrong"})
    assert r.status_code == 401
    r = client.post("/api/admin/login", json={"admin_id": "admin", "password": "looser@123"})
    assert r.status_code == 200, r.text
    admin = r.json()["token"]

    assert client.get("/api/me", headers=headers(farmer)).json()["role"] == "vendor"
    assert client.get("/api/me", headers=headers(buyer)).json()["role"] == "customer"
    assert client.get("/api/me", headers=headers(admin)).json()["role"] == "superadmin"
    assert client.get("/api/farmer/dashboard", headers=headers(buyer)).status_code == 403
    assert client.get("/api/admin/pending", headers=headers(buyer)).status_code == 403

    # Saved address create/dedupe/list/delete ownership
    addr_payload = {
        "kind": "delivery",
        "label": "Home",
        "data": {
            "house": "10-1",
            "line": "Main Road",
            "city": "Kadapa",
            "district": "Kadapa",
            "state": "Andhra Pradesh",
            "pin": "516001",
        },
    }
    r = client.post("/api/addresses", headers=headers(buyer), json=addr_payload)
    assert r.status_code == 200, r.text
    address_id = r.json()["id"]
    r2 = client.post("/api/addresses", headers=headers(buyer), json=addr_payload)
    assert r2.status_code == 200 and r2.json()["id"] == address_id
    listed = client.get("/api/addresses?kind=delivery", headers=headers(buyer)).json()
    assert len(listed) == 1
    assert client.delete(f"/api/addresses/{address_id}", headers=headers(buyer2)).status_code == 404

    # Crop submission, pending view, approval, public privacy.
    crop_id = create_crop(farmer)
    pending = client.get("/api/admin/pending", headers=headers(admin)).json()
    assert any(c["id"] == crop_id for c in pending)
    approved = approve_crop(admin, crop_id)
    assert approved["status"] == "approved" and approved["market_price"] == 25

    public_rows = client.get("/api/crops").json()
    public_crop = next(c for c in public_rows if c["id"] == crop_id)
    for private_key in (
        "farmer_phone", "farmer_name", "farmer_id", "location", "address_line",
        "village", "mandal", "district", "state", "pincode", "expected_price", "admin_note",
    ):
        assert private_key not in public_crop
    assert crop_id in [c["id"] for c in client.get("/api/crops?sort=price_asc").json()]
    assert client.get(f"/api/crops/{crop_id}").status_code == 200

    # Single booking validation: address required.
    r = client.post(
        "/api/bookings",
        headers=headers(buyer),
        json={"crop_id": crop_id, "quantity_kg": 10, "delivery_method": "delivery"},
    )
    assert r.status_code == 400 and "address" in r.text.lower()

    # Buyer order appears immediately in both buyer and farmer Bookings.
    r = client.post(
        "/api/bookings",
        headers=headers(buyer),
        json={
            "crop_id": crop_id,
            "quantity_kg": 10,
            "delivery_method": "delivery",
            "delivery_address": "10-1 Main Road, Kadapa, AP 516001",
        },
    )
    assert r.status_code == 200, r.text
    order_id = r.json()["id"]
    buyer_orders = client.get("/api/bookings", headers=headers(buyer)).json()
    farmer_orders = client.get("/api/bookings", headers=headers(farmer)).json()
    assert any(o["id"] == order_id for o in buyer_orders)
    assert any(o["id"] == order_id for o in farmer_orders)

    with SessionLocal() as db:
        assert db.get(Crop, crop_id).available_kg == 90

    # Farmer accepts -> admin confirms -> tracking -> shipped -> OTP -> delivered.
    r = client.patch(
        f"/api/bookings/{order_id}/decision",
        headers=headers(farmer),
        json={"action": "accept"},
    )
    assert r.status_code == 200 and r.json()["status"] == "farmer_pending_admin"

    # Buyer can still cancel only before admin confirms; this order will continue.
    r = client.patch(
        f"/api/admin/bookings/{order_id}/status",
        headers=headers(admin),
        json={"status": "farmer_accepted"},
    )
    assert r.status_code == 200 and r.json()["status"] == "farmer_accepted"
    assert client.patch(f"/api/bookings/{order_id}/cancel", headers=headers(buyer)).status_code == 400

    r = client.patch(
        f"/api/admin/bookings/{order_id}/status",
        headers=headers(admin),
        json={"status": "processing"},
    )
    assert r.status_code == 200 and r.json()["status"] == "processing"
    assert client.patch(
        f"/api/admin/bookings/{order_id}/status",
        headers=headers(admin), json={"status": "delivered"}
    ).status_code == 400

    r = client.patch(
        f"/api/admin/bookings/{order_id}/status",
        headers=headers(admin),
        json={"status": "shipped"},
    )
    assert r.status_code == 200 and r.json()["status"] == "shipped"
    buyer_order = next(o for o in client.get("/api/bookings", headers=headers(buyer)).json() if o["id"] == order_id)
    delivery_otp = buyer_order.get("delivery_otp")
    assert delivery_otp and len(delivery_otp) == 6 and delivery_otp.isdigit()

    wrong = "000000" if delivery_otp != "000000" else "111111"
    assert client.post(
        f"/api/admin/bookings/{order_id}/verify-delivery-otp",
        headers=headers(admin), json={"otp": wrong}
    ).status_code == 400
    r = client.post(
        f"/api/admin/bookings/{order_id}/verify-delivery-otp",
        headers=headers(admin), json={"otp": delivery_otp}
    )
    assert r.status_code == 200 and r.json()["status"] == "delivered"
    buyer_order = next(o for o in client.get("/api/bookings", headers=headers(buyer)).json() if o["id"] == order_id)
    assert buyer_order["status"] == "delivered" and "delivery_otp" not in buyer_order

    # Delivered review once only.
    r = client.post(
        f"/api/bookings/{order_id}/review",
        headers=headers(buyer), json={"rating": 5, "comment": "Good quality"}
    )
    assert r.status_code == 200, r.text
    assert client.post(
        f"/api/bookings/{order_id}/review",
        headers=headers(buyer), json={"rating": 4, "comment": "Again"}
    ).status_code == 400
    reviews = client.get(f"/api/crops/{crop_id}/reviews").json()
    assert reviews and reviews[0]["rating"] == 5

    # Farmer rejection restores reserved stock.
    r = client.post(
        "/api/bookings", headers=headers(buyer),
        json={"crop_id": crop_id, "quantity_kg": 10, "delivery_method": "delivery", "delivery_address": "Buyer Home"},
    )
    reject_id = r.json()["id"]
    with SessionLocal() as db:
        assert db.get(Crop, crop_id).available_kg == 80
    r = client.patch(
        f"/api/bookings/{reject_id}/decision", headers=headers(farmer),
        json={"action": "reject", "reason": "Crop unavailable today"},
    )
    assert r.status_code == 200 and r.json()["status"] == "farmer_rejected"
    with SessionLocal() as db:
        assert db.get(Crop, crop_id).available_kg == 90

    # Buyer cancellation restores reserved stock.
    r = client.post(
        "/api/bookings", headers=headers(buyer),
        json={"crop_id": crop_id, "quantity_kg": 10, "delivery_method": "delivery", "delivery_address": "Buyer Home"},
    )
    buyer_cancel_id = r.json()["id"]
    assert client.patch(f"/api/bookings/{buyer_cancel_id}/cancel", headers=headers(buyer)).status_code == 200
    with SessionLocal() as db:
        assert db.get(Crop, crop_id).available_kg == 90

    # Admin cancellation after farmer acceptance restores stock.
    r = client.post(
        "/api/bookings", headers=headers(buyer),
        json={"crop_id": crop_id, "quantity_kg": 10, "delivery_method": "delivery", "delivery_address": "Buyer Home"},
    )
    admin_cancel_id = r.json()["id"]
    assert client.patch(
        f"/api/bookings/{admin_cancel_id}/decision", headers=headers(farmer), json={"action": "accept"}
    ).status_code == 200
    r = client.patch(
        f"/api/admin/bookings/{admin_cancel_id}/status",
        headers=headers(admin), json={"status": "admin_cancelled", "reason": "Test cancellation"},
    )
    assert r.status_code == 200 and r.json()["status"] == "admin_cancelled"
    with SessionLocal() as db:
        assert db.get(Crop, crop_id).available_kg == 90

    # Cart checkout creates every order and reserves exact stock.
    crop2 = create_crop(farmer, name="Onion", qty=50)
    approve_crop(admin, crop2, price=30, qty=50)
    r = client.post(
        "/api/bookings/cart",
        headers=headers(buyer2),
        json={
            "items": [
                {"crop_id": crop_id, "quantity_kg": 10},
                {"crop_id": crop2, "quantity_kg": 20},
            ],
            "delivery_address": "Buyer Two Home",
        },
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["booking_ids"]) == 2
    assert r.json()["total"] == 850
    buyer2_orders = client.get("/api/bookings", headers=headers(buyer2)).json()
    for booking_id in r.json()["booking_ids"]:
        assert any(o["id"] == booking_id for o in buyer2_orders)

    # Low-stock rule: reserve down to <10, hidden from marketplace and direct detail.
    low_crop = create_crop(farmer, name="Brinjal", qty=20)
    approve_crop(admin, low_crop, price=40, qty=20)
    r = client.post(
        "/api/bookings", headers=headers(buyer),
        json={"crop_id": low_crop, "quantity_kg": 15, "delivery_method": "delivery", "delivery_address": "Buyer Home"},
    )
    assert r.status_code == 200, r.text
    assert low_crop not in [c["id"] for c in client.get("/api/crops").json()]
    assert client.get(f"/api/crops/{low_crop}").status_code == 404

    # Farmer can add stock and listing returns to marketplace.
    r = client.patch(
        f"/api/farmer/crops/{low_crop}/stock",
        headers=headers(farmer), json={"quantity_kg": 10}
    )
    assert r.status_code == 200 and r.json()["available_kg"] == 15
    assert low_crop in [c["id"] for c in client.get("/api/crops").json()]

    # Crop rejection and admin removal remain functional.
    rejected_crop = create_crop(farmer, name="Cabbage", qty=30)
    r = client.patch(
        f"/api/admin/crops/{rejected_crop}", headers=headers(admin),
        json={"action": "reject", "admin_note": "Quality check failed"},
    )
    assert r.status_code == 200 and r.json()["status"] == "rejected"

    removable_crop = create_crop(farmer, name="Carrot", qty=30)
    approve_crop(admin, removable_crop, price=35, qty=30)
    r = client.patch(
        f"/api/admin/crops/{removable_crop}/remove",
        headers=headers(admin), json={"reason": "Listing withdrawn by admin"},
    )
    assert r.status_code == 200 and r.json()["status"] == "removed"
    assert removable_crop not in [c["id"] for c in client.get("/api/crops").json()]

    # Notification list/read/dismiss and ownership.
    notifications = client.get("/api/notifications", headers=headers(buyer)).json()
    assert isinstance(notifications, list) and notifications
    notification_id = notifications[0]["id"]
    assert client.patch(
        f"/api/notifications/{notification_id}", headers=headers(buyer), json={"read": True}
    ).status_code == 200
    assert client.delete(f"/api/notifications/{notification_id}", headers=headers(buyer2)).status_code == 404
    assert client.delete(f"/api/notifications/{notification_id}", headers=headers(buyer)).status_code == 200

    # Dashboards and admin lists stay healthy.
    farmer_dashboard = client.get("/api/farmer/dashboard", headers=headers(farmer))
    assert farmer_dashboard.status_code == 200
    assert farmer_dashboard.json()["crops"] >= 5
    assert client.get("/api/farmer/crops", headers=headers(farmer)).status_code == 200
    assert client.get("/api/admin/vendors", headers=headers(admin)).status_code == 200
    assert client.get("/api/admin/bookings", headers=headers(admin)).status_code == 200
    assert client.get("/api/admin/analytics", headers=headers(admin)).status_code == 200

    # Address can be deleted by its owner.
    assert client.delete(f"/api/addresses/{address_id}", headers=headers(buyer)).status_code == 200


def test_static_javascript_contains_stability_fixes():
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "frontend" / "app.js").read_text(encoding="utf-8")
    admin_js = (root / "frontend" / "admin.js").read_text(encoding="utf-8")
    assert "placeCartOrdersBtn" in app_js
    assert "connectLive()" in app_js
    assert "Unavailable crops were removed from your cart" in app_js
    assert "location.protocol==='https:'?'wss':'ws'" in app_js
    assert "location.protocol==='https:'?'wss':'ws'" in admin_js


def test_admin_can_create_and_remove_other_admin():
    r = client.post("/api/admin/login", json={"admin_id": "admin", "password": "looser@123"})
    assert r.status_code == 200, r.text
    primary = r.json()["token"]

    r = client.post(
        "/api/admin/admins",
        headers=headers(primary),
        json={"admin_id": "operations.admin", "name": "Operations Admin", "password": "ops@12345"},
    )
    assert r.status_code == 200, r.text
    created = r.json()
    assert created["admin_id"] == "operations.admin"

    duplicate = client.post(
        "/api/admin/admins",
        headers=headers(primary),
        json={"admin_id": "operations.admin", "name": "Duplicate", "password": "ops@12345"},
    )
    assert duplicate.status_code == 409

    r = client.post("/api/admin/login", json={"admin_id": "operations.admin", "password": "ops@12345"})
    assert r.status_code == 200, r.text
    added_token = r.json()["token"]
    assert client.get("/api/admin/pending", headers=headers(added_token)).status_code == 200

    admins = client.get("/api/admin/admins", headers=headers(primary))
    assert admins.status_code == 200
    assert any(a["admin_id"] == "operations.admin" for a in admins.json())

    r = client.delete(f"/api/admin/admins/{created['id']}", headers=headers(primary))
    assert r.status_code == 200, r.text
    assert client.post("/api/admin/login", json={"admin_id": "operations.admin", "password": "ops@12345"}).status_code == 401
    assert client.get("/api/admin/pending", headers=headers(added_token)).status_code == 401


def test_same_phone_can_use_buyer_and_farmer_roles():
    phone = "9111111111"
    buyer_token = otp_login(phone, "buyer", "Dual Role User")
    farmer_token = otp_login(phone, "farmer", "Dual Role User")
    buyer_me = client.get('/api/me', headers=headers(buyer_token))
    farmer_me = client.get('/api/me', headers=headers(farmer_token))
    assert buyer_me.status_code == 200 and buyer_me.json()['role'] == 'customer'
    assert farmer_me.status_code == 200 and farmer_me.json()['role'] == 'vendor'
    assert buyer_me.json()['phone'] == farmer_me.json()['phone'] == phone
    assert buyer_me.json()['id'] != farmer_me.json()['id']

def test_frontend_cache_and_removed_demo_defaults():
    home = client.get('/')
    assert home.status_code == 200
    html = home.text
    assert 'Demo Buyer' not in html
    assert '9999999999' not in html
    assert '?v=75' in html
    js = client.get('/static/app.js')
    assert js.status_code == 200
    assert 'no-store' in js.headers.get('cache-control','')
    assert "prompt(t('How many kg do you want to add?'),'10')" not in js.text


def test_v75_admin_crop_edit_and_mobile_alignment_assets():
    admin_js = client.get('/static/admin.js').text
    css = client.get('/static/style.css').text
    assert 'editMarketCropPage' in admin_js
    assert '/edit' in admin_js
    assert 'v75 — mobile alignment cleanup' in css
    assert 'grid-template-columns:40px minmax(0,1fr) 40px 22px' in css


def test_cart_badge_counts_items_and_buyer_orders_split():
    js = client.get('/static/app.js').text
    assert "el.textContent=x.length" in js
    assert "el.textContent=getCart().length" in js
    assert "Active Orders" in js
    assert "Delivered Orders" in js
    assert "rows.filter(b=>b.status!=='delivered')" in js
    assert "rows.filter(b=>b.status==='delivered')" in js


def test_live_support_buyer_admin_flow():
    buyer = otp_login("9000000091", "buyer", "Support Buyer")
    r = client.post("/api/admin/login", json={"admin_id": "admin", "password": "looser@123"})
    assert r.status_code == 200, r.text
    admin = r.json()["token"]

    r = client.post("/api/support/tickets", headers=headers(buyer), json={
        "subject": "Delivery help",
        "category": "delivery",
        "message": "My order tracking needs help",
    })
    assert r.status_code == 200, r.text
    ticket = r.json()
    ticket_id = ticket["id"]
    assert ticket["status"] == "open"
    assert ticket["messages"][0]["sender_role"] == "buyer"

    mine = client.get("/api/support/tickets", headers=headers(buyer))
    assert mine.status_code == 200 and any(x["id"] == ticket_id for x in mine.json())

    all_tickets = client.get("/api/admin/support/tickets", headers=headers(admin))
    assert all_tickets.status_code == 200
    assert any(x["id"] == ticket_id and x["user_name"] == "Support Buyer" for x in all_tickets.json())

    reply = client.post(f"/api/admin/support/tickets/{ticket_id}/messages", headers=headers(admin), json={"message":"We are checking this now."})
    assert reply.status_code == 200, reply.text
    assert reply.json()["messages"][-1]["sender_role"] == "admin"

    user_reply = client.post(f"/api/support/tickets/{ticket_id}/messages", headers=headers(buyer), json={"message":"Thank you"})
    assert user_reply.status_code == 200, user_reply.text

    close = client.patch(f"/api/admin/support/tickets/{ticket_id}/status", headers=headers(admin), json={"status":"closed"})
    assert close.status_code == 200 and close.json()["status"] == "closed"
    blocked = client.post(f"/api/support/tickets/{ticket_id}/messages", headers=headers(buyer), json={"message":"hello"})
    assert blocked.status_code == 400
