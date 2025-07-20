import abc

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.core.database.repositories import BaseRepository


class AbstractUnitOfWork(abc.ABC):
    """
    Abstract base class for a unit of work.
    This class defines the interface for managing transactions and repositories.

    Subclasses must implement the `__aenter__` and `__aexit__` methods to handle session management.

    You can define specific repositories as attributes if needed just after docstrings.
    """

    @abc.abstractmethod
    async def __aenter__(self):
        """Enter the unit of work context, initializing the session."""
        raise NotImplementedError

    @abc.abstractmethod
    async def __aexit__(self, exc_type, exc_value, traceback):
        """Exit the unit of work context, committing or rolling back the session."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_repository(self, repo_type: type[BaseRepository]) -> BaseRepository:
        """Return the repository instance for the given repository type."""
        raise NotImplementedError


class UnitOfWork(AbstractUnitOfWork):
    """
    Concrete implementation of the AbstractUnitOfWork.
    This class manages the session lifecycle and provides access to repositories.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory
        self.session = None

    async def __aenter__(self):
        """Initialize the session."""
        self.session = self.session_factory()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Commit or rollback the session based on whether an exception occurred."""
        if exc_type is None:
            await self.session.commit()
        else:
            await self.session.rollback()
        await self.session.close()

    def get_repository(self, repo_type: type[BaseRepository]) -> BaseRepository:
        """
        Get a repository instance for the specified type.

        Args:
            repo_type: The type of repository to retrieve.

        Returns:
            An instance of the requested repository type.
        """
        return repo_type(self.session)