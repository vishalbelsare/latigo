from unittest.mock import Mock, patch

import pytest

from tests.factories.gordo import MachineFactory

parametrized_get_model_data = [
        (
            {
                "projects": ["project-1", "project-2"],
                "models": [
                    MachineFactory(project_name="project-1"),
                    MachineFactory(project_name="project-2"),
                    MachineFactory(project_name="project-2"),
                ],
            }
        ),
        (
            {
                "projects": ["project-1", "missing_project", "project-2"],
                "models": (
                    [
                        MachineFactory(project_name="project-1"),
                        MachineFactory(project_name="project-2"),
                        MachineFactory(project_name="project-2"),
                    ]
                ),
            }
        ),
    ]


@pytest.mark.parametrize("data", parametrized_get_model_data)
@patch("latigo.gordo.model_info_provider.GordoClientPool.get_auth_session", new=Mock())
def test_get_model_data(data, gordo_model_info_provider):
    projects = data.get("projects")
    expected_models = data.get("models")
    models_side_effects = []

    for project in projects:
        if project == "missing_project":
            models_side_effects.append(TypeError("byte indices must be integers or slices, not str"))
        else:
            models_side_effects.append([m for m in expected_models if m.project_name == project])

    with patch("latigo.gordo.client_pool.Client._get_machines", side_effect=models_side_effects):
        res = gordo_model_info_provider.get_model_data(projects=projects)
    assert res == expected_models
