import copy

from rest_framework.routers import Route, DefaultRouter, SimpleRouter, DynamicRoute


class MultiRouter(DefaultRouter):
    routes = copy.deepcopy(SimpleRouter.routes)
    routes[0].mapping.update({
        'delete': 'multi_destroy',
    })


class ListDetailRouter(SimpleRouter):
    routes = [
        Route(
            url=r'^{prefix}{trailing_slash}$',
            mapping={
                'get': 'list',
                'post': 'create',
                'patch': 'patch',
                'delete': 'delete'
            },
            name='{basename}-list',
            detail=False,
            initkwargs={'suffix': 'List'}
        ),
        DynamicRoute(
            url=r'^{prefix}/{url_path}{trailing_slash}$',
            name='{basename}-{url_name}',
            detail=False,
            initkwargs={}
        ),
        Route(
            url=r'^{prefix}/{lookup}{trailing_slash}$',
            mapping={
                'get': 'retrieve',
                'patch': 'partial_update',
                'delete': 'destroy'
            },
            name='{basename}-detail',
            detail=True,
            initkwargs={'suffix': 'Instance'}
        ),
        DynamicRoute(
            url=r'^{prefix}/{lookup}/{url_path}{trailing_slash}$',
            name='{basename}-{url_name}',
            detail=True,
            initkwargs={}
        ),
        # Route(
        #     url=r'^{prefix}/$',
        #     mapping={'get': 'retrieve'},
        #     name='{basename}-detail',
        #     detail=False,
        #     initkwargs={'suffix': 'Detail'}
        # ),
        # Route(
        #     url=r'^{prefix}/$',
        #     mapping={'patch': 'patch'},
        #     name='{basename}-patch',
        #     detail=False,
        #     initkwargs={'suffix': 'Patch'},
        # ),
        # Route(
        #     url=r'^{prefix}/$',
        #     mapping={'delete': 'delete'},
        #     name='{basename}-delete',
        #     detail=False,
        #     initkwargs={'suffix': 'Delete'},
        # ),
    ]
