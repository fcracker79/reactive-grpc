import logging
import typing

from rxgrpc.thread_pool import GRPCInvocation


T1 = typing.TypeVar('T1')
T2 = typing.TypeVar('T2')


_LOGGER = logging.getLogger('rxgrpc.mappers')


def grpc_invocation_map(transformer: typing.Callable[[T1], T2]) -> typing.Callable[[GRPCInvocation], GRPCInvocation]:
    def _f(g: GRPCInvocation) -> GRPCInvocation:
        return g.map(transformer)
    return _f
