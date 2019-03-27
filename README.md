[![build status](https://img.shields.io/travis/fcracker79/reactive-grpc/master.svg?style=flat-square)](https://travis-ci.org/fcracker79/reactive-grpc)

# reactive-grpc
A simple gRPC bridge to reactive streams.


Example: Given the following Protocol buffers definition:

```
syntax = "proto3";

package rxgrpc.test;

service TestService {
  rpc GetOneToOne(TestRequest) returns (TestResponse) {}
  rpc GetOneToStream(TestRequest) returns (stream TestResponse) {}
  rpc GetStreamToOne(stream TestRequest) returns (TestResponse) {}
  rpc GetStreamToStream(stream TestRequest) returns (stream TestResponse) {}
}

message TestRequest {
  string message = 1;
}

message TestResponse {
  string message = 1;
}
```

and a simple Servicer class:
```python
from test.proto.test_pb2_grpc import TestServiceServicer
from test.proto import test_pb2


class _Servicer(TestServiceServicer):
    def GetOneToOne(self, request: test_pb2.TestRequest, context):
        return test_pb2.TestResponse(message='response: {}'.format(request.message))

    def GetOneToStream(self, request, context):
        for i in range(3):
            yield test_pb2.TestResponse(message='response {}: {}'.format(i, request.message))

    def GetStreamToOne(self, request_iterator, context):
        return test_pb2.TestResponse(
            message='response: {}'.format(
                ', '.join(map(lambda d: d.message, request_iterator))
            )
        )

    def GetStreamToStream(self, request_iterator, context):
        yield from map(
            lambda d: test_pb2.TestResponse(message='response: {}'.format(d.message)),
            request_iterator
        )
```
A simple gRPC reactive server where request messages are transformed can be created as follows:

```python
from test.proto import test_pb2_grpc, test_pb2
from rxgrpc import server, mappers
from rx import operators
from test.proto.test_pb2_grpc import TestServiceServicer


class _Servicer(TestServiceServicer):
    # ...
    pass


workers = 3
rx_server = server.create_server(test_pb2, workers)
test_pb2_grpc.add_TestServiceServicer_to_server(_Servicer(), rx_server)
rx_server.add_insecure_port('[::]:50051')

def _transform_message(m: test_pb2.TestRequest) -> test_pb2.TestRequest:
    return test_pb2.TestRequest(message='TRANSFORMED {}'.format(m.message))

rx_server.set_grpc_observable(
    rx_server.grpc_pipe(
        operators.map(mappers.grpc_invocation_map(_transform_message)),
        method_name='/rxgrpc.test.TestService/GetOneToOne'),
    method_name='/rxgrpc.test.TestService/GetOneToOne'
)

rx_server.start()

```

Here it is an example of a filter for a streaming input:

```python
from rxgrpc import operators
from test.proto import test_pb2


def _filter_message(m: test_pb2.TestRequest) -> test_pb2.TestRequest:
    return bool(int(m.message[-1]) % 2)

server = ...
server.set_grpc_observable(
    server.grpc_pipe(
        operators.filter(_filter_message),
        method_name='/rxgrpc.test.TestService/GetStreamToOne'),
    method_name='/rxgrpc.test.TestService/GetStreamToOne'
)
```