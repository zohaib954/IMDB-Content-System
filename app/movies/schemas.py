from marshmallow import Schema, fields, validate, validates, ValidationError


VALID_SORT_OPTIONS = [
    "release_date_asc",
    "release_date_desc",
    "ratings_asc",
    "ratings_desc",
]


class MovieListQuerySchema(Schema):
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    page_size = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))
    year = fields.Int(load_default=None, allow_none=True)
    language = fields.Str(load_default=None, allow_none=True)
    sort_by = fields.Str(
        load_default=None,
        allow_none=True,
        validate=validate.OneOf(VALID_SORT_OPTIONS),
    )