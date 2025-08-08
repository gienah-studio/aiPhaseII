from .routes.virtual_order_routes import router as virtual_order_router
from .routes.bonus_pool_routes import router as bonus_pool_router

# Export the routers for use in the main application
__all__ = ['virtual_order_router', 'bonus_pool_router']
