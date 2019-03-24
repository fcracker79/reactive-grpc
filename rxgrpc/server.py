import typing

import grpc
# noinspection PyPackageRequirements
from google.protobuf.descriptor import MethodDescriptor
from rx import Observable

from rxgrpc import thread_pool


class GRPCObservableServer(thread_pool.GRPCObservable):
    def __init__(self, server: grpc.Server, grpc_observable_delegate: thread_pool.GRPCObservable):
        self.server = server
        self._grpc_observable_delegate = grpc_observable_delegate

    def grpc_pipe(
            self, *operators: typing.Callable[[Observable], Observable],
            method_name: typing.Optional[str] = None,
            method: typing.Optional[MethodDescriptor] = None):
        if bool(method_name) == bool(method):
            raise ValueError('You must specify either method_name or method')
        return self._grpc_observable_delegate.grpc_pipe(
            *operators, method_name=method_name, method=method)

    def grpc_subscribe(self):
        return self._grpc_observable_delegate.grpc_subscribe()

    def set_grpc_observable(
            self, new_observable: Observable,
            method_name: typing.Optional[str] = None,
            method: typing.Optional[MethodDescriptor] = None) -> None:
        if bool(method_name) == bool(method):
            raise ValueError('You must specify either method_name or method')
        return self._grpc_observable_delegate.set_grpc_observable(
            new_observable, method=method, method_name=method_name
        )

    def get_grpc_observable(
            self, method_name: typing.Optional[str] = None,
            method: typing.Optional[MethodDescriptor] = None) -> Observable:
        if bool(method_name) == bool(method):
            raise ValueError('You must specify either method_name or method')
        return self._grpc_observable_delegate.get_grpc_observable(
            method_name=method_name, method=method
        )


def create_server(protobuf_module, max_workers: int) -> GRPCObservableServer:
    tp = thread_pool.create(protobuf_module, max_workers)
    return GRPCObservableServer(grpc.server(tp), tp)
