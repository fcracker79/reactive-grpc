from rxgrpc import operators

from test.proto import test_pb2
from test.proto.test_pb2_grpc import TestServiceServicer
from test.rxgrpc_tests import BaseUnitTestCase


class TestFilters(BaseUnitTestCase):
    class _Servicer(TestServiceServicer):
        def GetOneToOne(self, request: test_pb2.TestRequest, context):
            return test_pb2.TestResponse(message='response: {}'.format(request.message))

        def GetOneToStream(self, request, context):
            for i in range(3):
                yield test_pb2.TestResponse(message='response {}: {}'.format(i, request.message))

        def GetStreamToOne(self, request_iterator, context):
            print('xxxxx {}'.format(list(request_iterator)))
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

    def test_message_transformation(self):
        def _transform_message(m: test_pb2.TestRequest) -> test_pb2.TestRequest:
            return test_pb2.TestRequest(message='TRANSFORMED {}'.format(m.message))

        server = self.create_server(self._Servicer())
        server.set_grpc_observable(
            server.grpc_pipe(
                operators.map(_transform_message),
                method_name='/rxgrpc.test.TestService/GetOneToOne'),
            method_name='/rxgrpc.test.TestService/GetOneToOne'
        )
        server.start()
        try:
            client = self.create_client()
            response = client.GetOneToOne(test_pb2.TestRequest(message='message0'))
            self.assertEqual(test_pb2.TestResponse, type(response))
            self.assertEqual('response: TRANSFORMED message0', response.message)
        finally:
            server.stop(None)

    def test_message_transformation_stream(self):
        def _filter_message(m: test_pb2.TestRequest) -> test_pb2.TestRequest:
            return bool(int(m.message[-1]) % 2)

        server = self.create_server(self._Servicer())
        server.set_grpc_observable(
            server.grpc_pipe(
                *operators.filter(_filter_message),
                method_name='/rxgrpc.test.TestService/GetStreamToOne'),
            method_name='/rxgrpc.test.TestService/GetStreamToOne'
        )
        server.start()
        try:
            client = self.create_client()
            response = client.GetStreamToOne(
                (test_pb2.TestRequest(message='message{}'.format(i)) for i in range(4))
            )
            self.assertEqual(test_pb2.TestResponse, type(response))
            self.assertEqual(
                'response: TRANSFORMED message1, TRANSFORMED message3',
                response.message)
        finally:
            server.stop(None)
