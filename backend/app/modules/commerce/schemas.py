from pydantic import BaseModel, Field


class CartItemAdd(BaseModel):
    product_public_id: str = Field(min_length=1, max_length=32)
    variant_public_id: str | None = Field(default=None, min_length=1, max_length=32)
    quantity: int = Field(default=1, ge=1)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1)


class CheckoutRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=7, max_length=32)
    email: str | None = Field(default=None, max_length=320)
    notes: str | None = Field(default=None, max_length=1000)
    payment_method_public_id: str | None = Field(default=None, min_length=1, max_length=32)


class OrderLookupRequest(BaseModel):
    """Public order lookup without magic tracking link."""

    order_number: str = Field(min_length=1, max_length=32)
    phone: str = Field(min_length=7, max_length=32)


class PaymentMethodResponse(BaseModel):
    public_id: str
    code: str
    name: str
    is_enabled: bool = True
    payment_type: str | None = None
    instructions: str | None = None
    callback_url: str | None = None
    callback_token: str | None = None


class PaymentMethodCreate(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=2, max_length=100)
    instructions: str | None = Field(default=None, max_length=2000)
    is_enabled: bool = True
    config: dict[str, str] | None = None


class PaymentMethodUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    instructions: str | None = Field(default=None, max_length=2000)
    is_enabled: bool | None = None
    config: dict[str, str] | None = None


class PaymentResponse(BaseModel):
    public_id: str
    status: str
    amount_minor: int
    currency: str
    method: PaymentMethodResponse
    failure_reason: str | None = None
    paid_at: str | None = None
    provider_reference: str | None = None


class PaymentListItemResponse(PaymentResponse):
    order_public_id: str
    order_number: str
    customer_first_name: str
    customer_last_name: str
    customer_phone: str
    attempt_count: int
    created_at: str


class CartItemResponse(BaseModel):
    public_id: str
    product_public_id: str
    product_name: str
    product_slug: str
    variant_public_id: str | None
    variant_label: str | None
    sku: str | None
    image_url: str | None
    quantity: int
    unit_price_minor: int
    line_total_minor: int
    currency: str


class CartResponse(BaseModel):
    public_id: str
    currency: str
    items: list[CartItemResponse]
    item_count: int
    subtotal_minor: int


class OrderStatusResponse(BaseModel):
    public_id: str
    code: str
    name: str
    description: str | None
    sort_order: int
    is_terminal: bool


class OrderStatusHistoryResponse(BaseModel):
    status: OrderStatusResponse
    source: str
    created_at: str


class OrderItemResponse(BaseModel):
    public_id: str
    product_public_id: str
    variant_public_id: str | None
    product_name: str
    variant_label: str | None
    sku: str | None
    quantity: int
    unit_price_minor: int
    line_total_minor: int


class OrderResponse(BaseModel):
    public_id: str
    order_number: str
    status: OrderStatusResponse
    store_name: str | None = None
    customer_first_name: str
    customer_last_name: str
    customer_email: str | None
    customer_phone: str
    notes: str | None
    currency: str
    subtotal_minor: int
    total_minor: int
    items: list[OrderItemResponse]
    created_at: str
    tracking_url: str | None = None
    payment: PaymentResponse | None = None


class OrderTrackingResponse(BaseModel):
    store_name: str
    order_number: str
    status: OrderStatusResponse
    status_history: list[OrderStatusHistoryResponse]
    customer_first_name: str
    currency: str
    subtotal_minor: int
    total_minor: int
    items: list[OrderItemResponse]
    created_at: str
    updated_at: str
    tracking_url: str
    payment: PaymentResponse | None = None


class OrderStatusUpdate(BaseModel):
    status_public_id: str = Field(min_length=1, max_length=32)
