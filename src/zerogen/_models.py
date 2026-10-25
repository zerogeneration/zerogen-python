import pydantic


class BaseModel(pydantic.BaseModel):
    """A response from the API. Fields it adds later are kept as extra fields."""

    model_config = pydantic.ConfigDict(
        extra="allow", validate_by_name=True, protected_namespaces=()
    )
