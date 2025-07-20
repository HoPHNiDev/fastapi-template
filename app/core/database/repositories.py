from typing import Type, TypeVar, Optional, List, Generic, Any

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.models import Base as SQLAlchemyBase
from app.core.utils import get_utc_now
from loggers import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=SQLAlchemyBase)


class BaseRepository(Generic[T]):
    """Base repository with common SQLAlchemy operations using context-managed sessions."""

    model: Type[T]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        if not hasattr(self, "model"):
            raise NotImplementedError("Subclasses must define class variable 'model'")

    async def create(self,
                     data: dict[str, Any],
                     commit: bool = False) -> Optional[T]:
        """Create a new record using the provided data."""
        instance = self.model(**data)
        self.session.add(instance)
        if commit:
            await self.session.commit()
            await self.session.refresh(instance)
        else:
            await self.session.flush()
        logger.info("%s created successfully.", self.model.__name__)
        return instance

    async def get_single(self,
                         allow_null_filters: bool = False,
                         **filters: Any) -> Optional[T]:
        """Retrieve a single record using the provided filters."""
        filters = self._clean_filters(filters, allow_null_filters)
        query = select(self.model).filter_by(**filters)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_list(self,
                       allow_null_filters: bool = False,
                       **filters: Any) -> List[T]:
        """Retrieve a list of records using the provided filters without pagination."""
        filters = self._clean_filters(filters, allow_null_filters)
        query = select(self.model).filter_by(**filters)

        order_by = getattr(self.model, "created_at", None)
        if order_by is None:
            order_by = getattr(self.model, "id", None)
        if order_by is not None:
            query = query.order_by(order_by.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_last_entry(self, order_field: str = "created_at", **filters: Any) -> Optional[T]:
        """
        Retrieve the most recent record based on the 'created_at' field.
        """
        query = select(self.model).limit(1).filter_by(**filters)

        order_by = getattr(self.model, order_field, None)
        if order_by is None:
            order_by = getattr(self.model, "id", None)
        if order_by is not None:
            query = query.order_by(order_by.desc())

        result = await self.session.execute(query)
        return result.scalars().first()


    async def get_paginated_list(self,
                                 allow_null_filters: bool = False,
                                 **filters: Any) -> Page[T]:
        """Retrieve a paginated list of records using the provided filters."""
        filters = self._clean_filters(filters, allow_null_filters)
        query = select(self.model).filter_by(**filters)

        order_by = getattr(self.model, "created_at", None)
        if order_by is None:
            order_by = getattr(self.model, "id", None)
        if order_by is not None:
            query = query.order_by(order_by.desc())

        return await self.paginate(query)

    async def update(self,
                     data: dict[str, Any],
                     allow_null_filters: bool = False,
                     commit: bool = False,
                     **filters: Any) -> Optional[T]:
        """Update a record using the provided data."""
        filters = self._clean_filters(filters, allow_null_filters)
        query = select(self.model).filter_by(**filters)
        result = await self.session.execute(query)
        instance = result.scalars().first()
        if instance:
            for key, value in data.items():
                setattr(instance, key, value)
            if commit:
                await self.session.commit()
                await self.session.refresh(instance)
            logger.info("%s updated successfully.", self.model.__name__)
            return instance
        return None

    async def delete(self,
                     commit: bool = False,
                     allow_null_filters: bool = False,
                     **filters: Any) -> Optional[T]:
        """Delete a record using the provided filters."""
        filters = self._clean_filters(filters, allow_null_filters)
        query = select(self.model).filter_by(**filters)
        result = await self.session.execute(query)
        instance = result.scalars().first()
        if instance:
            if commit:
                await self.session.delete(instance)
                await self.session.commit()
            logger.info("%s deleted successfully.", self.model.__name__)
            return instance #type: ignore
        return None

    @staticmethod
    def _clean_filters(filters: dict[str, Any], allow_null: bool) -> dict[str, Any]:
        return filters if allow_null else {k: v for k, v in filters.items() if v is not None}

    async def paginate(self, query):
        return await paginate(self.session, query)

class SoftDeleteRepository(BaseRepository[T], Generic[T]):
    """Repository with soft delete support."""

    async def get_single(self,
                         allow_null_filters: bool = False,
                         **filters: Any) -> Optional[T]:
        """Retrieve a single record where is_deleted flag is False, using the provided filters."""
        filters.setdefault("is_deleted", False)
        return await super().get_single(allow_null_filters, **filters)

    async def get_list(self,
                       allow_null_filters: bool = False,
                       **filters: Any) -> List[T]:
        """Retrieve a list of records where is_deleted flag is False, using the provided filters."""
        filters.setdefault("is_deleted", False)
        return await super().get_list(allow_null_filters, **filters)

    async def get_last_entry(self, order_field: str = "created_at", **filters: Any) -> Optional[T]:
        """Retrieve the most recent record based on the 'created_at' field, where is_deleted flag is False."""
        filters.setdefault("is_deleted", False)
        return await super().get_last_entry(order_field, **filters)

    async def get_paginated_list(self,
                                 allow_null_filters: bool = False,
                                 **filters: Any) -> Page[T]:
        """Retrieve a list of records where is_deleted flag is False, using the provided filters,
        with pagination."""
        filters.setdefault("is_deleted", False)
        return await super().get_paginated_list(allow_null_filters, **filters)

    async def update(self,
                     data: dict[str, Any],
                     allow_null_filters: bool = False,
                     commit: bool = True,
                     **filters: Any) -> Optional[T]:
        """Update a record where is_deleted flag is False, using the provided filters."""
        filters.setdefault("is_deleted", False)
        return await super().update(data, allow_null_filters, commit, **filters)

    async def delete(self,
                     commit: bool = True,
                     allow_null_filters: bool = False,
                     **filters: Any) -> Optional[T]:
        """Soft delete a record, using the provided filters."""
        filters.setdefault("is_deleted", False)
        filters = self._clean_filters(filters, allow_null_filters)
        query = select(self.model).filter_by(**filters)
        result = await self.session.execute(query)
        instance: Optional[T] = result.scalars().first()
        if instance:
            setattr(instance, "is_deleted", True)
            setattr(instance, "deleted_at", get_utc_now())
            if commit:
                await self.session.commit()
                await self.session.refresh(instance)
            logger.info("%s soft deleted successfully.", self.model.__name__)
            return instance
        return None