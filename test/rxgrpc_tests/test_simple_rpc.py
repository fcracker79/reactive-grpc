from test.proto import test_pb2
from test.proto.test_pb2_grpc import TestServiceServicer
from test.rxgrpc_tests import BaseUnitTestCase


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
