from datetime import datetime
from typing import Dict, List, Optional

import pytest

from typemapping.typemapping import get_nested_field_type


# Test Models
class Address:
    postal_code: str

    def __init__(self, street: str, number: int, city: str, country: str):
        self.street: str = street
        self.number: int = number
        self.city: str = city
        self.country: str = country
        self.postal_code: str = "12345"

    def get_full_address(self) -> str:
        return f"{self.number} {self.street}, {self.city}, {self.country}"

    @property
    def location_info(self) -> Dict[str, str]:
        return {"city": self.city, "country": self.country}


class Department:
    def __init__(self, name: str, budget: float, manager_name: Optional[str] = None):
        self.name: str = name
        self.budget: float = budget
        self.manager_name: Optional[str] = manager_name
        self.employee_count: int = 10

    def get_budget(self) -> float:
        return self.budget

    @property
    def is_large(self) -> bool:
        return self.employee_count > 50


class Person:
    def __init__(self, name: str, age: int, email: str, address: Address):
        self.name: str = name
        self.age: int = age
        self.email: str = email
        self.address: Address = address
        self.employee_id: str = "EMP001"
        self.birth_date: datetime = datetime(1990, 1, 1)

    def get_age(self) -> int:
        return self.age

    @property
    def full_name(self) -> str:
        return self.name.upper()


class Company:
    founded: int

    def __init__(self, name: str, ceo: Person, departments: List[Department]):
        self.name: str = name
        self.ceo: Person = ceo
        self.departments: List[Department] = departments
        self.founded: int = 2010
        self.stock_price: float = 150.50

    def get_ceo(self) -> Person:
        return self.ceo

    @property
    def years_active(self) -> int:
        return 2024 - self.founded


# ============= SIGCHECK TESTS =============


def test_sigcheck_nested_fields_valid():
    """Test that valid nested field injections pass signature check."""

    field_type_map = {
        "name": str,
        "founded": int,
        "ceo.name": str,
        "ceo.age": int,
        "ceo.address.city": str,
        "ceo.address.street": str,
        "ceo.address.location_info": Dict[str, str],
        "get_ceo.age": int,
        "ceo.address.get_full_address": str,
        "years_active": int,
        "ceo.address.postal_code": str,
        "ceo.full_name": str,
        "ceo.address.country": str,
        "get_ceo": Person,
        "ceo.get_age": int,
    }

    for field, expected_type in field_type_map.items():
        field_type = get_nested_field_type(Company, field)
        assert (
            field_type == expected_type
        ), f"Field '{field}' expected type {expected_type}, got {field_type}"


def test_sigcheck_nonexistent_fields():
    """Test that non-existent nested fields are caught."""

    field_type_map = [
        "ceo.invalid_field",
        "ceo.address.invalid_field",
        "nonexistent.field.path",
    ]
    for field in field_type_map:
        ftype = get_nested_field_type(Company, field)
        assert (
            ftype is None
        ), f"Expected None for non-existent field '{field}', got {ftype}"


def test_inject_deep_nesting():
    """Test very deep nesting (4+ levels)."""

    # Create a deeply nested structure
    class Country:

        def __init__(self, name: str, code: str):
            self.name: str = name
            self.code: str = code

        @property
        def continent(self) -> str:
            return "North America"

    class City:

        def __init__(self, name: str, country: Country):
            self.name: str = name
            self.country: Country = country

        def population(self) -> int:
            return 1000000

    class ExtendedAddress:
        def __init__(self, street: str, city: City):
            self.street: str = street
            self.city: City = city

    class ExtendedPerson:
        def __init__(self, name: str, address: ExtendedAddress):
            self.name: str = name
            self.address: ExtendedAddress = address

    class ExtendedCompany:
        def __init__(self, ceo: ExtendedPerson):
            self.ceo: ExtendedPerson = ceo

    field_type_map = {
        "ceo.address.city.country.name": str,
        "ceo.address.city.country.code": str,
        "ceo.address.city.country.continent": str,
        "ceo.address.city.name": str,
        "ceo.address.city.population": int,
    }
    for field, expected_type in field_type_map.items():
        field_type = get_nested_field_type(ExtendedCompany, field)
        assert (
            field_type == expected_type
        ), f"Field '{field}' expected type {expected_type}, got {field_type}"


if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v"])
