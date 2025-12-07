"""
Provider 顺序管理服务

启动时同步 provider 顺序：
1. 数据库中已有的 provider 保持原有顺序
2. 新增的 provider 自动追加到末尾
3. 已删除的 provider 从数据库中移除
"""
from sqlalchemy import select, delete, func

from database.config import db_manager
from database.models import ProviderOrder
from providers.manager import ProvidersManager
from logger import get_logger

log = get_logger("provider_order")

_ordered_providers: list[dict] = []


async def sync_provider_order():
    """
    同步 provider 顺序到数据库

    逻辑：
    1. 数据库中已有的 provider 保持原有顺序
    2. 新增的 provider 追加到末尾（按名称排序）
    3. 代码中已删除的 provider 从数据库移除
    """
    global _ordered_providers

    mgr = ProvidersManager()
    available = {name: mgr.get_adapter_achieve(name) for name in mgr.available_plugins()}
    available_names = set(available.keys())

    async with db_manager.get_session() as session:
        # 获取数据库中现有的顺序
        result = await session.execute(
            select(ProviderOrder).order_by(ProviderOrder.sort_order)
        )
        db_orders = {po.provider_name: po for po in result.scalars().all()}
        db_names = set(db_orders.keys())

        # 删除已不存在的 provider
        to_delete = db_names - available_names
        if to_delete:
            await session.execute(
                delete(ProviderOrder).where(ProviderOrder.provider_name.in_(to_delete))
            )
            log.info(f"移除已删除的 provider: {to_delete}")

        # 新增的 provider 追加到末尾
        to_add = available_names - db_names
        if to_add:
            # 获取当前最大 sort_order
            max_result = await session.execute(select(func.max(ProviderOrder.sort_order)))
            max_order = max_result.scalar() or -1

            for name in sorted(to_add):
                max_order += 1
                session.add(ProviderOrder(provider_name=name, sort_order=max_order))
            log.info(f"新增 provider: {sorted(to_add)}")

        await session.commit()

        # 重新查询构建内存缓存
        result = await session.execute(
            select(ProviderOrder).order_by(ProviderOrder.sort_order)
        )
        _ordered_providers = []
        for po in result.scalars().all():
            adapter = available.get(po.provider_name)
            if adapter:
                _ordered_providers.append({
                    "name": po.provider_name,
                    "home": getattr(adapter, "home", po.provider_name),
                    "free": getattr(adapter, "FREE", False),
                    "pay": getattr(adapter, "PAY", False),
                })

        log.info(f"Provider 顺序: {[p['name'] for p in _ordered_providers]}")


def get_ordered_providers() -> list[dict]:
    """获取排序后的 provider 列表"""
    return _ordered_providers
