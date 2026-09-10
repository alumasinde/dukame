"""
Tenant-scoped repository pattern for DukaMe.

All queries that touch tenant-owned data must include explicit tenant filtering.
This pattern document helps prevent accidental cross-tenant data leaks.

RULE: Every query touching user data, orders, shops, etc. must explicitly
      filter by tenant_id in the WHERE clause.

Example (SAFE):
    async def get_order(db: AsyncSession, order_id: int, tenant_id: int) -> Order:
        return await db.scalar(
            select(Order)
            .where(Order.id == order_id, Order.tenant_id == tenant_id)
        )

Example (UNSAFE - DO NOT DO THIS):
    async def get_order(db: AsyncSession, order_id: int) -> Order:
        return await db.scalar(select(Order).where(Order.id == order_id))
        # BUG: Missing tenant_id filter! Cross-tenant access possible!

Best Practice:
    1. All repository methods that accept order_id, shop_id, etc. MUST also
       accept tenant_id (or get it from current_user context).
    2. Add tenant_id to the WHERE clause of EVERY query:
       - select()
       - update()
       - delete()
    3. Use dependency injection to pass current tenant:
       - from app.modules.tenancy.dependencies import get_current_tenant
       - Then include tenant_id in all queries automatically.
    4. Write tests that verify cross-tenant access is DENIED.
"""
