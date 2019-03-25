import logging
import typing

from rxgrpc.thread_pool import GRPCInvocation

_LOGGER = logging.getLogger('rxgrpc.filters')

T = typing.TypeVar('T')


def filter(f: typing.Callable[[T], bool]) -> typing.Callable[[GRPCInvocation], bool]:
    def _f(g: GRPCInvocation) -> bool:
        input_message = g.input_message()
        try:
            iter(input_message)
            return True
        except TypeError:
            return f(input_message)
    return _f
