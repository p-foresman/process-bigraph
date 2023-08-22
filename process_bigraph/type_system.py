"""
=============
Process Types
=============
"""

from bigraph_schema import TypeSystem
from process_bigraph.registry import protocol_registry



process_interval_schema = {
    '_type': 'float',
    '_apply': 'set',
    '_default': '1.0'}


# TODO: implement these
def apply_process(current, update, bindings=None, types=None):
    process_schema = dict(types.access('process'))
    process_schema.pop('_apply')
    return types.apply(
        process_schema,
        current,
        update)


def divide_process(value, bindings=None, types=None):
    return value


def serialize_process(value, bindings=None, types=None):
    # TODO -- need to get back the protocol: address and the config
    return value


DEFAULT_INTERVAL = 1.0


def deserialize_process(serialized, bindings=None, types=None):
    protocol, address = serialized['address'].split(':', 1)

    process_lookup = protocol_registry.access(protocol)
    if not process_lookup:
        raise Exception(f'protocol "{protocol}" not implemented')
    instantiate = process_lookup(address)

    config = types.hydrate_state(
        instantiate.config_schema,
        serialized.get('config', {}))

    interval = types.deserialize(
        process_interval_schema,
        serialized.get('interval'))

    # this instance always acts like a process no matter
    # where it is running
    process = instantiate(config)
    deserialized = serialized.copy()
    deserialized['instance'] = process
    deserialized['config'] = config
    deserialized['interval'] = interval

    return deserialized


def deserialize_step(serialized, bindings=None, types=None):
    protocol, address = serialized['address'].split(':', 1)

    lookup = protocol_registry.access(protocol)
    if not lookup:
        raise Exception(f'protocol "{protocol}" not implemented')
    instantiate = lookup(address)

    config = types.hydrate_state(
        instantiate.config_schema,
        serialized.get('config', {}))

    # this instance always acts like a process no matter
    # where it is running
    process = instantiate(config)
    deserialized = serialized.copy()
    deserialized['instance'] = process
    deserialized['config'] = config

    return deserialized


process_types = {
    'protocol': {
        '_super': 'string'},

    # TODO: step wires are directional ie, we make a distinction
    #   between inputs and outputs, and the same wire cannot be both
    #   an input and output at the same time
    'step': {
        '_super': ['edge'],
        '_apply': 'apply_process',
        '_serialize': 'serialize_process',
        '_deserialize': 'deserialize_step',
        '_divide': 'divide_process',
        '_description': '',
        # TODO: support reference to type parameters from other states
        'address': 'protocol',
        'config': 'tree[any]'},

    'process': {
        '_super': ['edge'],
        '_apply': 'apply_process',
        '_serialize': 'serialize_process',
        '_deserialize': 'deserialize_process',
        '_divide': 'divide_process',
        '_description': '',
        # TODO: support reference to type parameters from other states
        'interval': process_interval_schema,
        'address': 'protocol',
        'config': 'tree[any]'},
}


def register_process_types(types):
    types.apply_registry.register('apply_process', apply_process)
    types.serialize_registry.register('serialize_process', serialize_process)
    types.deserialize_registry.register('deserialize_process', deserialize_process)
    types.divide_registry.register('divide_process', divide_process)

    types.deserialize_registry.register('deserialize_step', deserialize_step)

    for process_key, process_type in process_types.items():
        types.type_registry.register(process_key, process_type)

    return types


class ProcessTypes(TypeSystem):
    def __init__(self):
        super().__init__()
        register_process_types(self)

    # def serialize(self, schema, state):
    #     return ''

    # def deserialize(self, schema, encoded):
    #     return {}

    def infer_schema(self, schema, state):
        schema = schema or {}
        if isinstance(state, dict):
            import ipdb; ipdb.set_trace()

            if '_type' in state:
                state_type = state['_type']
                state_schema = self.access(state_type)
                # TODO: fix is_descendant
                # if types.type_registry.is_descendant('process', state_schema) or types.registry.is_descendant('step', state_schema):
                if state_type == 'process' or state_type == 'step':
                    edge_instance = self.deserialize(state_schema, state)
                    # TODO: retain the process instance and reuse
                    # TODO: iterate through process wires and generate
                    #   missing composition for every wire entry
                    return {
                        '_type': state_type,
                        '_ports': edge_instance['instance'].schema()}
                else:
                    return state_type
            else:
                inferred_schema = {}
                for key, value in state.items():
                    # TODO: check to see if the state matches the given schema
                    inner_schema = schema.get(key)
                    if inner_schema:
                        access = self.access(inner_schema)
                        # TODO: do validation
                        # self.validate_state(access, value)
                        inferred_schema[key] = access
                    else:
                        # TODO: get missing schema for states from
                        #   the wires and ports of the process
                        inner_schema = self.infer_schema(
                            schema.get(key),
                            value)
                        if inner_schema:
                            inferred_schema[key] = inner_schema

                return schema
        else:
            return schema
        

    def hydrate_state(self, schema, state):
        if isinstance(state, str) or '_deserialize' in schema:
            result = self.deserialize(schema, state)
        elif isinstance(state, dict):
            result = {
                key: self.hydrate_state(schema[key], state[key])
                for key, value in state.items()}
        return result

    def hydrate(self, schema, state):
        hydrated = self.hydrate_state(schema, state)
        return self.fill(schema, hydrated)

    def dehydrate(self, schema):
        return {}

    def lookup_address(self, address):
        protocol, config = address.split(':')

        if protocol == 'local':
            self.lookup_local(config)


types = ProcessTypes()
