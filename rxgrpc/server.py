import grpc

from rxgrpc import thread_pool


class GRPCObservableServer(thread_pool.GRPCObservable):
    def __init__(self, server: grpc.Server, grpc_observable_delegate: thread_pool.GRPCObservable):
        self.server = server
        self._grpc_observable_delegate = grpc_observable_delegate

    def grpc_pipe(self, *a, **kw):
        return self._grpc_observable_delegate.grpc_pipe(*a, **kw)

    def grpc_subscribe(self):
        return self._grpc_observable_delegate.grpc_subscribe()

    def set_grpc_observable(self, *a, **kw):
        return self._grpc_observable_delegate.set_grpc_observable(*a, **kw)

    def get_grpc_observable(self, **kw):
        return self._grpc_observable_delegate.get_grpc_observable(**kw)


def create_server(protobuf_module, max_workers: int) -> GRPCObservableServer:
    tp = thread_pool.create(protobuf_module, max_workers)
    return GRPCObservableServer(grpc.server(tp), tp)
