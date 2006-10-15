from rdflib.Graph import QuotedGraph
from rdflib.events import Event, Dispatcher
from rdflib.store import TripleAddedEvent, TripleRemovedEvent, StoreCreatedEvent


class JournalWriter(object):
    """
    Writes a journal of the store events.
    """

    def __init__(self, store, stream=None, filename=None):
        if stream is None:
            assert filename, "Must specify either stream or filename"
            stream = file(filename, "ab")
        dispatcher = store.dispatcher
        dispatcher.subscribe(TripleAddedEvent, self.journal_event)
        dispatcher.subscribe(TripleRemovedEvent, self.journal_event)
        dispatcher.subscribe(StoreCreatedEvent, self.journal_event)
        self._dumps = store.node_pickler.dumps
        self._write = stream.write

    def journal_event(self, event):
        self._write(self._dumps(event))
        self._write("\n\n")


class JournalReader(object):
    """
    Reads a journal of store events into a store.
    """

    def __init__(self, store, filename):
        self.stream = file(filename, "rb")
        self.store = store
        dispatcher = Dispatcher()
        dispatcher.subscribe(TripleAddedEvent, self.add)
        dispatcher.subscribe(TripleRemovedEvent, self.remove)
        dispatcher.subscribe(StoreCreatedEvent, self.store_created)
        loads = store.node_pickler.loads
        dispatch = dispatcher.dispatch
        lines = []
        for line in self.stream:
            if line=="\n":
                event = loads("".join(lines))
                dispatch(event)
                lines = []
            else:
                lines.append(line)

    def add(self, event):
        context = event.context
        quoted = isinstance(context, QuotedGraph)
        self.store.add(event.triple, context, quoted)

    def remove(self, event):
        self.store.remove(event.triple, event.context)
        
    def store_created(self, event):
        assert len(self.store)==0, "Store created events in the middle of a journal are not yet supported"
        # TODO: clear store