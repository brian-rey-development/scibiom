import pytest

from scibiom_api.transport.error_handlers import DOMAIN_ERROR_STATUS
from scibiom_core.kernel import errors
from scibiom_core.kernel.errors import DomainError


def _kernel_error_types(base: type[DomainError] = DomainError) -> list[type[DomainError]]:
    found = [
        subclass for subclass in base.__subclasses__() if subclass.__module__ == errors.__name__
    ]
    return found + [nested for subclass in found for nested in _kernel_error_types(subclass)]


@pytest.mark.parametrize("error_type", _kernel_error_types())
def test_every_kernel_domain_error_has_a_status_mapping(error_type: type[DomainError]) -> None:
    assert error_type in DOMAIN_ERROR_STATUS
