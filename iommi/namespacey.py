from tri_declarative import (
    declarative,
    flatten,
    Namespace,
    Refinable,
)
from tri_declarative.refinable import is_refinable_function


class RefinedNamespace(Namespace):
    __iommi_refined_delta: str
    __iommi_refined_parent: Namespace
    __iommi_refined_delta: Namespace
    __iommi_refined_defaults: bool

    def __init__(self, description, parent, defaults=False, *args, **kwargs):
        delta = Namespace(*args, **kwargs)
        object.__setattr__(self, '__iommi_refined_description', description)
        object.__setattr__(self, '__iommi_refined_parent', parent)
        object.__setattr__(self, '__iommi_refined_delta', delta)
        object.__setattr__(self, '__iommi_refined_defaults', defaults)
        if defaults:
            super().__init__(delta, parent)
        else:
            super().__init__(parent, delta)

    def as_stack(self):
        refinements = []
        default_refinements = []
        node = self

        while isinstance(node, RefinedNamespace):
            try:
                description = object.__getattribute__(node, '__iommi_refined_description')
                parent = object.__getattribute__(node, '__iommi_refined_parent')
                delta = object.__getattribute__(node, '__iommi_refined_delta')
                defaults = object.__getattribute__(node, '__iommi_refined_defaults')
                value = (description, flatten(delta))
                if defaults:
                    default_refinements = default_refinements + [value]
                else:
                    refinements = [value] + refinements
                node = parent
            except AttributeError:
                break

        return default_refinements + [('base', flatten(node))] + refinements


class NamespaceyMeta(type):
    def __call__(cls, *args, namespace=None, **kwargs):
        namespace = Namespace(namespace) if namespace is not None else Namespace()
        for name in list(kwargs):
            prefix, _, _ = name.partition('__')
            if isinstance(getattr(cls, prefix, None), Refinable):
                namespace.setitem_path(name, kwargs.pop(name))
        instance: Namespacey = super().__call__(*args, **kwargs)
        instance.namespace = namespace
        return instance


@declarative(
    member_class=Refinable,
    parameter='refinable_members',
    is_member=is_refinable_function,
    add_init_kwargs=False,
)
class Namespacey(metaclass=NamespaceyMeta):
    namespace: Namespace
    finalized: bool = False

    def refine(self, **args):
        assert not self.finalized, f"{self} already finalized"
        return type(self)(namespace=RefinedNamespace('refine', self.namespace, **args))

    def refine_defaults(self, **args):
        assert not self.finalized, f"{self} already finalized"
        return type(self)(namespace=RefinedNamespace('refine defaults', self.namespace, defaults=True, **args))

    def finalize(self):
        assert not self.finalized, f"{self} already finalized"

        kwargs = self.namespace
        declared_items = self.get_declared('refinable_members')
        for k, v in declared_items.items():
            if isinstance(v, Refinable):
                setattr(self, k, kwargs.pop(k, None))
            else:
                if k in kwargs:
                    setattr(self, k, kwargs.pop(k))

        if kwargs:
            available_keys = '\n    '.join(sorted(declared_items.keys()))
            raise TypeError(
                f"""'{self.__class__.__name__}' object has no refinable attribute(s): {', '.join(sorted(kwargs.keys()))}.
        Available attributes:
            {available_keys}""")

        self.finalized = True

        return self
