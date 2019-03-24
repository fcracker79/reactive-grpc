import typing

import grpc
# noinspection PyPackageRequirements
from google.protobuf.descriptor import MethodDescriptor
from rx import Observable
from rx.disposable import Disposable

from rxgrpc import thread_pool


class GRPCObservableServer(thread_pool.GRPCObservable):
    def __init__(self, server: grpc.Server, grpc_observable_delegate: thread_pool.GRPCObservable):
        self.server = server
        self._grpc_observable_delegate = grpc_observable_delegate
        self._disposable = None

    def grpc_pipe(
            self, *operators: typing.Callable[[Observable], Observable],
            method_name: typing.Optional[str] = None,
            method: typing.Optional[MethodDescriptor] = None):
        if bool(method_name) == bool(method):
            raise ValueError('You must specify either method_name or method')
        return self._grpc_observable_delegate.grpc_pipe(
            *operators, method_name=method_name, method=method)

    def grpc_subscribe(self) -> Disposable:
        if self._disposable:
            return self._disposable
        self._disposable = self._grpc_observable_delegate.grpc_subscribe()
        return self._disposable

    def set_grpc_observable(
            self, new_observable: Observable,
            method_name: typing.Optional[str] = None,
            method: typing.Optional[MethodDescriptor] = None) -> None:
        if self._disposable:
            raise ValueError('Already subscribed, cannot change observables')
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

    def add_insecure_port(self, address: str):
        self.server.add_insecure_port(address)

    def add_secure_port(self, address: str, server_credentials: grpc.ServerCredentials):
        self.server.add_secure_port(address, server_credentials)

    def start(self):
        self.grpc_subscribe()
        self.server.start()

    def stop(self, grace_time_secs: typing.Optional[float] = None):
        self.server.stop(grace_time_secs)

    def add_generic_rpc_handlers(self, generic_rpc_handlers):
        self.server.add_generic_rpc_handlers(generic_rpc_handlers)


def create_server(protobuf_module, max_workers: int) -> GRPCObservableServer:
    tp = thread_pool.create(protobuf_module, max_workers)
    return GRPCObservableServer(grpc.server(tp), tp)
