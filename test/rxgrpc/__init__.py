import unittest

import grpc

from rxgrpc import server
from rxgrpc.server import GRPCObservableServer
from test.proto import test_pb2, test_pb2_grpc


class BaseUnitTestCase(unittest.TestCase):
    @classmethod
    def create_server(cls, servicer: test_pb2_grpc.TestServiceServicer, workers: int=1) -> GRPCObservableServer:
        s = server.create_server(test_pb2, workers)
        test_pb2_grpc.add_TestServiceServicer_to_server(servicer, s.server)
        s.server.add_insecure_port('[::]:50051')
        return s

    @classmethod
    def create_client(cls) -> test_pb2_grpc.TestServiceStub:
        channel = grpc.insecure_channel('localhost:50051')
        return test_pb2_grpc.TestServiceStub(channel)
