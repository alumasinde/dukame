from app.modules.commerce._service_impl import *  # noqa: F401,F403
from app.modules.commerce._service_impl import CommerceService as _CommerceService
from app.modules.catalogue.models.store import Store
from app.modules.commerce.models.order import Order


class CommerceService(_CommerceService):
    async def lookup_public_order(self, store: Store, order_number: str, phone: str) -> Order:
        from app.modules.commerce.order_lookup import lookup_order_by_phone

        return await lookup_order_by_phone(self.db, store, order_number, phone)
