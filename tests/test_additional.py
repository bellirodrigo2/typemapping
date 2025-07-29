"""Additional tests to improve coverage"""

from typing import Any, Dict, List, Optional, Set, Union

import pytest

from typemapping import (
    VarTypeInfo,
    debug_type_info,
    defensive_issubclass,
    extended_isinstance,
    generic_issubclass,
    get_annotated_metadata,
    get_args,
    get_compatibility_chain,
    get_equivalent_origin,
    get_field_type,
    get_origin,
    is_annotated_type,
    is_equal_type,
    map_init_field,
    map_model_fields,
    strip_annotated,
    unwrap_partial,
)


# Test compat.py functions
class TestCompatFunctions:
    """Test compatibility layer functions"""

    def test_get_origin_none(self):
        """Test get_origin with None"""
        assert get_origin(None) is None

    def test_get_args_none(self):
        """Test get_args with None"""
        assert get_args(None) == ()

    def test_strip_annotated_non_annotated(self):
        """Test strip_annotated with non-Annotated type"""
        assert strip_annotated(int) is int
        assert strip_annotated(List[str]) == List[str]

    def test_get_annotated_metadata_non_annotated(self):
        """Test get_annotated_metadata with non-Annotated type"""
        assert get_annotated_metadata(int) == ()
        assert get_annotated_metadata(List[str]) == ()

    def test_is_annotated_type_edge_cases(self):
        """Test is_annotated_type edge cases"""
        assert not is_annotated_type(None)
        assert not is_annotated_type(int)
        assert not is_annotated_type("string")


# Test VarTypeInfo methods
class TestVarTypeInfoMethods:
    """Test VarTypeInfo methods not covered elsewhere"""

    def test_isinstance_check(self):
        """Test isinstance_check method"""
        vti = VarTypeInfo("x", int, int, 42, has_default=True)
        assert vti.isinstance_check(42)
        assert not vti.isinstance_check("string")

        # Test with None basetype
        vti_none = VarTypeInfo("y", None, None, None)
        assert vti_none.isinstance_check(None)
        assert not vti_none.isinstance_check(42)

    def test_isinstance_check_error(self):
        """Test isinstance_check with type that causes error"""
        vti = VarTypeInfo("x", "InvalidType", "InvalidType", None)
        assert not vti.isinstance_check(42)

    def test_get_all_instances(self):
        """Test get_all_instances method"""

        class Meta1:
            pass

        class Meta2:
            pass

        m1, m2 = Meta1(), Meta2()
        vti = VarTypeInfo("x", str, str, m1, has_default=True, extras=(m2, "text"))

        # Should find both m1 (from default) and m2 (from extras)
        instances = vti.get_all_instances(Meta1)
        assert len(instances) == 1
        assert instances[0] is m1

        instances = vti.get_all_instances(Meta2)
        assert len(instances) == 1
        assert instances[0] is m2

    def test_getinstance_invalid_type(self):
        """Test getinstance with non-type argument"""
        vti = VarTypeInfo("x", str, str, "default", has_default=True)
        assert vti.getinstance("not_a_type") is None
        assert vti.getinstance(42) is None


# Test error handling in core functions
class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_get_field_type_errors(self):
        """Test get_field_type error cases"""

        class TestClass:
            @property
            def bad_prop(self):
                raise RuntimeError("Property error")

        # Should handle property access errors gracefully
        assert get_field_type(TestClass, "bad_prop") is None

    def test_defensive_issubclass_edge_cases(self):
        """Test defensive_issubclass with various edge cases"""
        # None input
        assert not defensive_issubclass(None, str)

        # Non-class input
        assert not defensive_issubclass("not_a_class", str)
        assert not defensive_issubclass(42, int)

        # Recursive error simulation
        class RecursiveType:
            pass

        # Should handle gracefully
        assert not defensive_issubclass(RecursiveType, "invalid")

    def test_extended_isinstance_sampling(self):
        """Test extended_isinstance with large containers"""
        # Create a large list to trigger sampling
        large_list = list(range(1000))
        assert extended_isinstance(large_list, List[int])

        # Mixed types should fail - put string in first 10 elements to ensure it's caught
        large_list[5] = "string"  # Within sampling range
        assert not extended_isinstance(large_list, List[int])

        # Test that sampling might miss errors beyond sample size
        large_list_2 = list(range(1000))
        large_list_2[500] = "string"  # Beyond typical sampling range
        # This might pass due to sampling - documenting the behavior
        result = extended_isinstance(large_list_2, List[int])
        # If sampling only checks first N elements, this would be True
        print(f"String at position 500 detected: {not result}")

    def test_extended_isinstance_any(self):
        """Test extended_isinstance with Any type"""
        assert extended_isinstance([1, "2", None], List[Any])
        assert extended_isinstance({"a": 1, "b": "2"}, Dict[str, Any])


# Test origins.py functions
class TestOriginsFunctions:
    """Test origins module functions"""

    def test_get_equivalent_origin_generic(self):
        """Test get_equivalent_origin with generic types"""

        class CustomGeneric:
            __origin__ = None

        # Should return None for unknown generic
        result = get_equivalent_origin(CustomGeneric)
        assert result is CustomGeneric or result is None

    def test_debug_type_info(self):
        """Test debug_type_info function"""
        info = debug_type_info(List[int])
        assert info["type"] == List[int]
        assert info["origin"] is list
        assert info["args"] == (int,)
        assert info["is_generic"] is True
        assert "module" in info

    def test_get_compatibility_chain_unknown(self):
        """Test get_compatibility_chain with unknown type"""

        class UnknownType:
            pass

        chain = get_compatibility_chain(UnknownType)
        assert chain == [UnknownType]


# Test type_check.py edge cases
class TestTypeCheckEdgeCases:
    """Test type checking edge cases"""

    def test_is_equal_type_none_cases(self):
        """Test is_equal_type with None"""
        assert is_equal_type(None, None)
        assert not is_equal_type(None, int)
        assert not is_equal_type(int, None)

    def test_generic_issubclass_none_cases(self):
        """Test generic_issubclass with None"""
        assert not generic_issubclass(None, int)
        assert not generic_issubclass(int, None)
        assert not generic_issubclass(None, None)

    def test_extended_isinstance_union_optional(self):
        """Test extended_isinstance with Union and Optional"""
        # Union type
        assert extended_isinstance(42, Union[int, str])
        assert extended_isinstance("test", Union[int, str])
        assert not extended_isinstance(3.14, Union[int, str])

        # Optional type
        assert extended_isinstance(None, Optional[int])
        assert extended_isinstance(42, Optional[int])
        assert not extended_isinstance("test", Optional[int])

    def test_validate_set_args(self):
        """Test validation of set arguments"""
        test_set = {1, 2, 3}
        assert extended_isinstance(test_set, Set[int])

        test_set_mixed = {1, "2", 3}
        assert not extended_isinstance(test_set_mixed, Set[int])

        # Empty set
        empty_set = set()
        assert extended_isinstance(empty_set, Set[int])

    def test_validate_mapping_any_types(self):
        """Test mapping validation with Any types"""
        test_dict = {"a": 1, "b": "2", "c": None}
        assert extended_isinstance(test_dict, Dict[Any, Any])
        assert extended_isinstance(test_dict, Dict[str, Any])
        assert not extended_isinstance(test_dict, Dict[Any, int])


# Test partial function handling
class TestPartialFunctions:
    """Test partial function unwrapping"""

    def test_unwrap_partial_not_partial(self):
        """Test unwrap_partial with regular function"""

        def regular_func(x: int) -> int:
            return x

        func, args, kwargs = unwrap_partial(regular_func)
        assert func is regular_func
        assert args == []
        assert kwargs == {}

    def test_complex_nested_partial(self):
        """Test deeply nested partial functions"""
        from functools import partial

        def base(a: int, b: str, c: float, d: bool) -> str:
            return f"{a}-{b}-{c}-{d}"

        # Create complex nested partial
        p1 = partial(base, 1)
        p2 = partial(p1, "test")
        p3 = partial(p2, c=3.14)

        func, args, kwargs = unwrap_partial(p3)
        assert func is base
        assert args == [1, "test"]
        assert kwargs == {"c": 3.14}


# Test model field mapping strategies
class TestFieldMappingStrategies:
    """Test different field mapping strategies"""

    def test_map_model_fields_with_property_side_effects(self):
        """Test map_model_fields handles properties safely"""

        class ModelWithDangerousProperty:
            x: int = 1

            @property
            def dangerous(self) -> str:
                raise RuntimeError("Should not be called!")

            def method(self) -> None:
                pass

        # Should not raise even with dangerous property
        fields = map_model_fields(ModelWithDangerousProperty)
        assert len(fields) == 1
        assert fields[0].name == "x"

    def test_map_init_field_no_init(self):
        """Test map_init_field with class using object.__init__"""

        class NoInit:
            pass

        fields = map_init_field(NoInit)
        assert fields == []


# Test convenience functions
class TestConvenienceFunctions:
    """Test convenience functions from typemapping module"""

    def test_extract_metadata(self):
        """Test extract_metadata function"""
        from typemapping.typemapping import extract_metadata

        class Meta:
            pass

        m = Meta()
        vti = VarTypeInfo("x", str, str, None, extras=(m, "text"))

        result = extract_metadata(vti, Meta)
        assert len(result) == 1
        assert result[0] is m

    def test_has_metadata(self):
        """Test has_metadata function"""
        from typemapping.typemapping import has_metadata

        class Meta:
            pass

        vti = VarTypeInfo("x", str, str, None, extras=(Meta(), "text"))
        assert has_metadata(vti, Meta)
        assert not has_metadata(vti, int)

    def test_filter_fields_by_metadata(self):
        """Test filter_fields_by_metadata function"""
        from typemapping.typemapping import filter_fields_by_metadata

        class Meta:
            pass

        fields = [
            VarTypeInfo("x", str, str, None, extras=(Meta(),)),
            VarTypeInfo("y", int, int, None),
            VarTypeInfo("z", float, float, None, extras=(Meta(),)),
        ]

        filtered = filter_fields_by_metadata(fields, Meta)
        assert len(filtered) == 2
        assert filtered[0].name == "x"
        assert filtered[1].name == "z"

    def test_group_fields_by_type(self):
        """Test group_fields_by_type function"""
        from typemapping.typemapping import group_fields_by_type

        fields = [
            VarTypeInfo("x", str, str, None),
            VarTypeInfo("y", int, int, None),
            VarTypeInfo("z", str, str, None),
            VarTypeInfo("w", None, None, None),  # None basetype
        ]

        groups = group_fields_by_type(fields)
        assert len(groups) == 2
        assert len(groups[str]) == 2
        assert len(groups[int]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
