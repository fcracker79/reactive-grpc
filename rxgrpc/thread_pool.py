import abc
import logging
import threading
import typing
from concurrent.futures import thread

import rx
# noinspection PyPackageRequirements
from google.protobuf.descriptor import MethodDescriptor
from rx import Observable
from rx.concurrency import ThreadPoolScheduler
from rx.core import Observer
from rx.core.abc import Scheduler, Disposable
from rx.disposable import CompositeDisposable
from rx.operators import observe_on

_LOGGER = logging.getLogger('rxgrpc.thread_pool')


def _log(msg: str, *a):
    _LOGGER.debug('[Thread %s] %s', threading.current_thread().getName(), msg, *a)


class GRPCInvocation(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def run(self):
        pass

    @abc.abstractmethod
    def add_done_callback(self, done_callback):
        pass

    @property
    @abc.abstractmethod
    def result(self):
        pass

    @abc.abstractmethod
    def map(self, transformer: typing.Callable[[typing.Any], typing.Any]) -> 'GRPCInvocation':
        pass


class _GRPCInvocation(GRPCInvocation):
    def __init__(self, fun: callable, rpc_event, state, behaviour, argument_thunk, a, kw):
        self.fun = fun
        self.rpc_event = rpc_event
        self.state = state
        self.behaviour = behaviour
        self.argument_thunk = argument_thunk
        self.a = a
        self.kw = kw
        self._result = None
        self._done_callbacks = []
        self._done = False
        self._transform = lambda d: d

    def map(self, transformer: typing.Callable[[typing.Any], typing.Any]) -> GRPCInvocation:
        result = _GRPCInvocation(
            self.fun, self.rpc_event, self.state,
            self.behaviour, self.argument_thunk, self.a, self.kw)
        result._done_callbacks.extend(self._done_callbacks)
        result._transform = transformer
        return result

    def run(self):
        _log('grpc invocation run')
        self._result = self.fun(
            self.rpc_event, self.state, self.behaviour,
            lambda: self._transform(self.argument_thunk()),
            *self.a, **self.kw)
        _log('grpc invocation run complete, result')
        self._done = True
        self._run_callbacks()

    def add_done_callback(self, done_callback):
        _log('adding callback')
        self._done_callbacks.append(done_callback)
        if self._done:
            self._run_callbacks()

    @property
    def result(self):
        return self._result

    def _run_callbacks(self):
        _log('running callbacks')
        for c in self._done_callbacks:
            c(self)


class DuckTypingThreadPool(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def submit(self, fun: callable, rpc_event, state, behaviour, argument_thunk, *a, **kw) -> GRPCInvocation:
        pass


class GRPCObservable(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def grpc_pipe(
            self, *operators: typing.Callable[[Observable], Observable],
            method_name: typing.Optional[str] = None,
            method: typing.Optional[MethodDescriptor] = None) -> Observable:
        pass

    @abc.abstractmethod
    def grpc_subscribe(self) -> Disposable:
        pass

    @abc.abstractmethod
    def set_grpc_observable(
            self, new_observable: Observable,
            method_name: typing.Optional[str] = None,
            method: typing.Optional[MethodDescriptor] = None) -> None:
        pass

    @abc.abstractmethod
    def get_grpc_observable(
            self, method_name: typing.Optional[str] = None,
            method: typing.Optional[MethodDescriptor] = None) -> Observable:
        pass


class _ReactiveThreadPool(GRPCObservable, DuckTypingThreadPool):
    def __init__(self, protobuf_module, max_workers: int):
        self.observers = {}  # type: typing.Dict[str, typing.List[Observer]]
        self.observables = {}  # type: typing.Dict[str, Observable]
        self._observable_to_be_subscribed = {}  # type: typing.Dict[str, Observable]

        pb_descriptor = protobuf_module.DESCRIPTOR
        for service in pb_descriptor.services_by_name.values():
            for method in service.methods:
                full_method_name = self._get_method_name(method=method)
                self._add_observer(full_method_name)
                self._observable_to_be_subscribed[full_method_name] = observe_on(ThreadPoolScheduler(max_workers))(
                    self.get_grpc_observable(method_name=full_method_name)
                )

    def grpc_subscribe(self) -> Disposable:
        disposables = []
        for observable in self._observable_to_be_subscribed.values():
            disposables.append(observable.subscribe(
                Observer(
                    on_next=lambda grpc_invocation: grpc_invocation.run(),
                    on_error=lambda e: _log('Error: ', e)
                )
            ))
        self._observable_to_be_subscribed.clear()
        return CompositeDisposable(*disposables)

    def grpc_pipe(self, *operators: typing.Callable[[Observable], Observable], **kw) -> Observable:
        pipe = self.get_grpc_observable(**kw).pipe(*operators)
        self.set_grpc_observable(pipe, **kw)
        return pipe

    def set_grpc_observable(self, new_observable: Observable, **kw):
        new_observable = observe_on(ThreadPoolScheduler(1))(new_observable)
        method_name = self._get_method_name(**kw)
        if method_name not in self._observable_to_be_subscribed:
            _LOGGER.exception('Method name {} not found, kw: {}'.format(method_name, kw))
            raise KeyError
        self.observables[method_name] = new_observable
        self._observable_to_be_subscribed[method_name] = new_observable

    def submit(self, fun: callable, rpc_event, state, behaviour, argument_thunk, *a, **kw):
        _log('submit')
        method = rpc_event.call_details.method.decode()
        grpc_invocation = _GRPCInvocation(fun, rpc_event, state, behaviour, argument_thunk, a, kw)
        for observer in self.observers[method]:
            observer.on_next(grpc_invocation)
        return grpc_invocation

    @classmethod
    def _get_method_name(
            cls,
            method_name: typing.Optional[str] = None,
            method: typing.Optional[MethodDescriptor] = None):
        if method_name:
            return method_name
        if method:
            return '/{service_full_name}/{method_name}'.format(
                service_full_name=method.containing_service.full_name,
                method_name=method.name)

    def _get_observers(self, **kw) -> typing.Sequence[Observer]:
        return self.observers[self._get_method_name(**kw)]

    def get_grpc_observable(self, **kw) -> Observable:
        try:
            return self.observables[self._get_method_name(**kw)]
        except KeyError:
            _LOGGER.exception('Could not find observable, kw: %s', kw)
            raise

    def _add_observer(self, path: str):
        # noinspection PyUnusedLocal
        def _f(observer: Observer, scheduler: typing.Optional[Scheduler]):
            self.observers.setdefault(path, []).append(observer)

        # noinspection PyTypeChecker
        self.observables[path] = rx.create(_f)


def create(protobuf_module, max_workers: int) \
        -> typing.Union[thread.ThreadPoolExecutor, GRPCObservable]:
    return _ReactiveThreadPool(protobuf_module, max_workers)
