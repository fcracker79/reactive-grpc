import typing

from rxgrpc.thread_pool import GRPCInvocation


T1 = typing.TypeVar('T1')
T2 = typing.TypeVar('T2')


def grpc_invocation_map(transformer: typing.Callable[[T1], T2]) -> typing.Callable[[GRPCInvocation], GRPCInvocation]:
    class _DelegateTransformationGRPCInvocation(GRPCInvocation):
        def __init__(self, delegate: GRPCInvocation):
            self._delegate = delegate

        def run(self):
            return self._delegate.run()

        def add_done_callback(self, done_callback):
            return self._delegate.add_done_callback(done_callback)

        @property
        def result(self):
            return transformer(self._delegate.result)

    return _DelegateTransformationGRPCInvocation
