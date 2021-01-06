import json
from pathlib import Path

import pytest
from django.views.decorators.csrf import csrf_exempt

from iommi import (
    Form,
    Page,
    register_style,
)
from iommi._web_compat import HttpResponse
from iommi.live_edit import (
    dangerous_execute_code,
    get_wrapped_view,
    live_edit_view,
    Middleware,
    orig_reload,
    should_edit,
    style_editor__edit,
    style_editor__new,
    style_editor__select,
    style_showcase,
)
from iommi.part import render_root
from iommi.style import unregister_style
from tests.helpers import req
from tests.models import TFoo


def view(request):
    return HttpResponse('hello!')   # pragma: no cover


class PageView(Page):
    hello = 'hello!'


@csrf_exempt
def csrf_exempt_view(request):
    return HttpResponse('hello!')   # pragma: no cover


def test_live_edit():
    result = render_root(part=live_edit_view(req('get'), csrf_exempt_view).bind(request=req('get')))
    assert '@csrf_exempt' in result, result
    assert "def csrf_exempt_view(request):" in result, result


def test_live_edit_dispatch_error(settings):
    settings.DEBUG = True
    m = Middleware(lambda _: 'response')
    request = req('get', _iommi_live_edit='bad data')
    assert m(request) == 'response'
    with pytest.raises(KeyError):
        m.process_view(request, None, None, None)


def test_get_wrapped_view_function():
    assert get_wrapped_view(view) is view
    assert get_wrapped_view(csrf_exempt(view)) is view
    get_wrapped_view(Form.create(auto__model=TFoo).as_view())


def test_should_edit(settings):
    assert not should_edit(req('get'))
    assert not should_edit(req('get', _iommi_live_edit=''))

    settings.DEBUG = True
    assert should_edit(req('get', _iommi_live_edit=''))


def test_dangerous_execute_code_error():
    with pytest.raises(SyntaxError):
        dangerous_execute_code(code='invalid code', request=req('post'), view=view)


def test_dangerous_execute_code_success():
    code = """
def view(request):
    return HttpResponse(request.GET['foo'] + 'bar')    
"""

    request = req('get', foo='foo')
    new_view = dangerous_execute_code(code=code, request=request, view=view)
    assert new_view(request).content.decode() == 'foobar'


def test_edit(capsys):
    path = Path(__file__).parent.parent / 'tests' / 'edit_views_temp.py'

    orig_code = """
from iommi._web_compat import HttpResponse

def foo_view(request):
    return HttpResponse('foo view data')        
"""

    new_code = """
def foo_view(request):
    return HttpResponse('changed!')        
"""

    with open(path, 'w') as f:
        f.write(orig_code)

    from tests.edit_views_temp import foo_view

    # Broken changes are NOT written to disk
    data = json.loads(live_edit_view(req('post', data='syntax error!'), foo_view).content)
    assert data == {'error': 'invalid syntax (<string>, line 1)'}

    with open(path) as f:
        assert f.read() == orig_code

    # Broken changes are NOT written to disk, this time with the exception string empty
    data = json.loads(live_edit_view(req('post', data='assert False'), foo_view).content)
    assert data == {'error': "<class 'AssertionError'>"}

    with open(path) as f:
        assert f.read() == orig_code

    # Valid changes are written to disk
    data = json.loads(live_edit_view(req('post', data=new_code), foo_view).content)
    assert data == {'page': 'changed!'}

    with open(path) as f:
        actual_new_code = f.read()

    assert actual_new_code == orig_code.replace('foo view data', 'changed!')

    # Reload trigger hack
    if orig_reload is not None:  # modern django

        from django.utils import autoreload
        autoreload.trigger_reload('notused')
        captured = capsys.readouterr()
        assert captured.out == 'Skipped reload\n'

        with pytest.raises(SystemExit):
            autoreload.trigger_reload('notused')


def test_style_editor__select():
    style_editor__select().bind(request=req('get')).render_to_response()


def test_showcase():
    request = req('get')
    style_showcase(request).bind(request=request).render_to_response()


def test_edit_style(settings, capsys):
    settings.DEBUG = True
    path = Path(__file__).parent.parent / 'tests' / 'edit_style_temp.py'

    orig_code = """
from iommi.style import Style
from iommi.style_base import base
test_edit_style = Style(
    base,
    Field=dict(),
)
"""

    new_code = """
from iommi.style import Style
from iommi.style_base import base
test_edit_style = Style(
    base,
    Form=dict(),
)
"""

    with open(path, 'w') as f:
        f.write(orig_code)

    from tests.edit_style_temp import test_edit_style
    register_style('test_edit_style', test_edit_style)

    # Broken changes are NOT written to disk
    data = json.loads(style_editor__edit(req('post', data='syntax error!', name='test_edit_style')).content)
    assert data == {'error': 'invalid syntax (<string>, line 1)'}

    with open(path) as f:
        assert f.read() == orig_code

    # Valid changes are written to disk
    data = json.loads(style_editor__edit(req('post', data=new_code, name='test_edit_style')).content)
    assert '<title>Style showcase</title>' in data['page']

    with open(path) as f:
        actual_new_code = f.read()

    assert actual_new_code == orig_code.replace('Field', 'Form')

    # Reload trigger hack
    if orig_reload is not None:  # modern django

        from django.utils import autoreload
        autoreload.trigger_reload('notused')
        captured = capsys.readouterr()
        assert captured.out == 'Skipped reload\n'

        with pytest.raises(SystemExit):
            autoreload.trigger_reload('notused')

    unregister_style('test_edit_style')


def test_style_editor__new():
    style_editor__new().bind(request=req('post', module='tests.style_editor_new_tmp', **{'-submit': ''})).render_to_response()
