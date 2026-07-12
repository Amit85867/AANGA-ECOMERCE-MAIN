"""Python enums mirroring the PostgreSQL enum types in the schema.

`name=` must match the Postgres type name so SQLAlchemy binds to the existing
type instead of trying to recreate it. `create_type=False` is set on the
column definitions since the types already exist in Supabase.
"""
import enum


class AccountType(str, enum.Enum):
    retail = "retail"
    wholesale = "wholesale"


class AuthProviderType(str, enum.Enum):
    email = "email"
    google = "google"
    phone = "phone"
    facebook = "facebook"


class OrderStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    packed = "packed"
    shipped = "shipped"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancelled = "cancelled"
    return_requested = "return_requested"
    returned = "returned"


class PaymentMethod(str, enum.Enum):
    upi = "upi"
    credit_card = "credit_card"
    debit_card = "debit_card"
    net_banking = "net_banking"
    wallet = "wallet"
    emi = "emi"
    cod = "cod"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"
    partially_refunded = "partially_refunded"


class TrackingStatusType(str, enum.Enum):
    placed = "placed"
    confirmed = "confirmed"
    packed = "packed"
    dispatched = "dispatched"
    in_transit = "in_transit"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    failed_attempt = "failed_attempt"
    returned = "returned"


class ReturnReason(str, enum.Enum):
    size_issue = "size_issue"
    wrong_item = "wrong_item"
    damaged = "damaged"
    quality_issue = "quality_issue"
    not_as_described = "not_as_described"
    changed_mind = "changed_mind"
    other = "other"


class ReturnStatus(str, enum.Enum):
    requested = "requested"
    approved = "approved"
    pickup_scheduled = "pickup_scheduled"
    picked_up = "picked_up"
    inspected = "inspected"
    resolved = "resolved"
    rejected = "rejected"


class ResolutionType(str, enum.Enum):
    refund = "refund"
    exchange = "exchange"
    store_credit = "store_credit"


class DiscountType(str, enum.Enum):
    percentage = "percentage"
    flat = "flat"


class VolumeRange(str, enum.Enum):
    below_10k = "below_10k"
    range_10k_50k = "10k_50k"
    range_50k_1lac = "50k_1lac"
    above_1lac = "above_1lac"


class InquiryStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    converted = "converted"
    rejected = "rejected"


class ContactSubject(str, enum.Enum):
    general = "general"
    order_support = "order_support"
    wholesale = "wholesale"
    returns_refunds = "returns_refunds"
    feedback = "feedback"
    other = "other"


class MessageStatus(str, enum.Enum):
    unread = "unread"
    read = "read"
    replied = "replied"
    closed = "closed"


class OfferType(str, enum.Enum):
    percentage_off = "percentage_off"
    flat_off = "flat_off"
    free_shipping = "free_shipping"
    bogo = "bogo"


class AdminRole(str, enum.Enum):
    master = "master"
    staff = "staff"
