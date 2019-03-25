from rx import operators

from rxgrpc.mappers import grpc_invocation_map
from test.proto import test_pb2
from test.proto.test_pb2_grpc import TestServiceServicer
from test.rxgrpc import BaseUnitTestCase


class TestSimpleRPC(BaseUnitTestCase):
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

    def test_one_to_one(self):
        server = self.create_server(self._Servicer())
        server.start()
        try:
            client = self.create_client()
            response = client.GetOneToOne(test_pb2.TestRequest(message='message0'))
            self.assertEqual(test_pb2.TestResponse, type(response))
            self.assertEqual('response: message0', response.message)
        finally:
            server.stop(None)

    def test_one_to_stream(self):
        server = self.create_server(self._Servicer())
        server.start()
        try:
            client = self.create_client()
            responses = list(client.GetOneToStream(test_pb2.TestRequest(message='message0')))
            self.assertEqual(3, len(responses))
            for i, response in enumerate(responses):
                self.assertEqual(test_pb2.TestResponse, type(response))
                self.assertEqual('response {}: message0'.format(i), response.message)
        finally:
            server.stop(None)

    def test_stream_to_one(self):
        server = self.create_server(self._Servicer())
        server.start()
        try:
            client = self.create_client()
            response = client.GetStreamToOne(
                (test_pb2.TestRequest(message='message{}'.format(i)) for i in range(3))
            )
            self.assertEqual(test_pb2.TestResponse, type(response))
            self.assertEqual('response: message0, message1, message2', response.message)
        finally:
            server.stop(None)

    def test_stream_to_stream(self):
        server = self.create_server(self._Servicer())
        server.start()

        responses = []
        try:
            client = self.create_client()
            responses.extend(
                client.GetStreamToStream(
                    (test_pb2.TestRequest(message='message{}'.format(i)) for i in range(3))
                )
            )
            self.assertEqual(3, len(responses))
            for i, response in enumerate(responses):
                self.assertEqual(test_pb2.TestResponse, type(response))
                self.assertEqual('response: message{}'.format(i), response.message)
        finally:
            server.stop(None)

    def test_message_transformation(self):
        def _transform_message(m: test_pb2.TestRequest) -> test_pb2.TestRequest:
            return test_pb2.TestRequest(message='TRANSFORMED {}'.format(m.message))

        server = self.create_server(self._Servicer())
        server.set_grpc_observable(
            server.grpc_pipe(
                operators.map(grpc_invocation_map(_transform_message)),
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
        def _transform_message(m: test_pb2.TestRequest) -> test_pb2.TestRequest:
            return test_pb2.TestRequest(message='TRANSFORMED {}'.format(m.message))

        server = self.create_server(self._Servicer())
        server.set_grpc_observable(
            server.grpc_pipe(
                operators.map(grpc_invocation_map(_transform_message)),
                method_name='/rxgrpc.test.TestService/GetStreamToOne'),
            method_name='/rxgrpc.test.TestService/GetStreamToOne'
        )
        server.start()
        try:
            client = self.create_client()
            response = client.GetStreamToOne(
                (test_pb2.TestRequest(message='message{}'.format(i)) for i in range(3))
            )
            self.assertEqual(test_pb2.TestResponse, type(response))
            self.assertEqual(
                'response: TRANSFORMED message0, TRANSFORMED message1, TRANSFORMED message2',
                response.message)
        finally:
            server.stop(None)
