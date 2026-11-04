import pytest

from app.study_plans.dependency_network import DependencyNetwork


def test_dependency_network_traverses_prerequisites_and_orders_study():
    dependencies = DependencyNetwork()
    dependencies.add_activity(40)
    dependencies.add_dependency(30, 20)
    dependencies.add_dependency(30, 10)
    dependencies.add_dependency(20, 10)

    assert dependencies.prerequisites_for(30) == (20, 10)
    assert dependencies.breadth_first(30) == [30, 20, 10]
    assert dependencies.depth_first(30) == [30, 20, 10]
    assert dependencies.study_order() == [10, 20, 30, 40]


def test_dependency_network_rejects_self_duplicate_and_circular_dependencies():
    dependencies = DependencyNetwork()
    dependencies.add_dependency(2, 1)
    with pytest.raises(ValueError, match="itself"):
        dependencies.add_dependency(2, 2)
    with pytest.raises(ValueError, match="already exists"):
        dependencies.add_dependency(2, 1)
    with pytest.raises(ValueError, match="cycle"):
        dependencies.add_dependency(1, 2)
