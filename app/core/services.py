from typing import Optional, Generic, TypeVar, List, Any

from fastapi_pagination import Page
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.models import Base as SQLAlchemyBase
from app.core.database.repositories import BaseRepository
from app.core.database.uow import AbstractUnitOfWork
from app.core.schemas import Base as PydanticBase

T = TypeVar("T", bound=SQLAlchemyBase)
CreateSchema = TypeVar("CreateSchema", bound=PydanticBase)
UpdateSchema = TypeVar("UpdateSchema", bound=PydanticBase)
RepoType = TypeVar("RepoType", bound=BaseRepository)  # type: ignore


class BaseService(Generic[T, CreateSchema, UpdateSchema, RepoType]):
    """Base service with common CRUD operations using Pydantic models."""

    repo_type: type[RepoType]

    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    async def create(self, data: CreateSchema) -> Optional[T]:
        """Create a new record using the provided session."""
        return await self.repository.create(data.model_dump())

    async def get_single(self,
                         allow_null_filters: bool = False,
                         **filters: Any) -> Optional[T]:
        return await self.repository.get_single(allow_null_filters, **filters)

    async def get_list(self,
                       allow_null_filters: bool = False,
                       **filters: Any) -> Page[T]:
        """Retrieve a list of records matching the filters using the provided session."""
        return await self.repository.get_list(allow_null_filters, **filters)

    async def get_list_without_pagination(self,
                                          allow_null_filters: bool = False,
                                          **filters: Any) -> List[T]:
        """Retrieve a list of records matching the filters using the provided session."""
        return await self.repository.get_list_without_pagination(allow_null_filters, **filters)

    async def update(self,
                     data: UpdateSchema,
                     allow_null_filters: bool = False,
                     **filters: Any) -> Optional[T]:
        """Update a record matching the filters using the provided session."""
        return await self.repository.update(
                                            data.model_dump(exclude_unset=True),
                                            allow_null_filters,
                                            **filters)

    async def delete(self,
                     allow_null_filters: bool = False,
                     **filters: Any) -> Optional[T]:
        """Delete a record matching the filters using the provided session."""
        return await self.repository.delete(allow_null_filters, **filters)

    @property
    def repository(self) -> RepoType:
        """Return the repository instance."""
        return self.uow.get_repository(self.repo_type)