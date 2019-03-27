import logging
import typing

from rx import operators as orig_operators, Observable

from rxgrpc.mappers import grpc_invocation_map, grpc_invocation_filter

T1 = typing.TypeVar('T1')
T2 = typing.TypeVar('T2')


_LOGGER = logging.getLogger('rxgrpc.mappers')


def _composite(*operators: typing.Callable[[Observable], Observable]) -> typing.Callable[[Observable], Observable]:
    def _f(o: Observable):
        for op in operators:
            o = op(o)
        return o
    return _f


def map(transformer: typing.Callable[[T1], T2]) -> typing.Callable[[Observable], Observable]:
    return orig_operators.map(grpc_invocation_map(transformer))


_base_filter = filter


def filter(f: typing.Callable[[T1], bool]):
    return orig_operators.map(grpc_invocation_filter(f))
