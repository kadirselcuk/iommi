from django.db.models import QuerySet
from tri_declarative import (
    Namespace,
    refinable,
)

MISSING = object()


def evaluated_refinable(f):
    f = refinable(f)
    f.__iommi__evaluated = True
    return f


def model_and_rows(model, rows):
    if rows is None and model is not None:
        rows = model.objects.all()

    if model is None and isinstance(rows, QuerySet):
        model = rows.model

    return model, rows


def create_as_view_from_as_page(cls, name, *, kwargs, title, parts):
    def view_wrapper(request, **url_kwargs):
        return getattr(cls(**kwargs), f'{name}_page')(title=title, parts=parts, **url_kwargs).bind(request=request).render_to_response()

    view_wrapper.__name__ = f'{cls.__name__}{repr(Namespace(kwargs))[len("Namespace"):]}.{name}_view'
    view_wrapper.__doc__ = cls.__doc__

    return view_wrapper


