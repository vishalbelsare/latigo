from os import environ

environ['LATIGO_INTERNAL_DATABASE']="sqlite:///latigo_offset_persistence.db"

from latigo.offset_persistence import DBOffsetPersistance, MemoryOffsetPersistance

class TestOffsetPersistence:

    def test_get_set(self):
        op=MemoryOffsetPersistance()
        #DBOffsetPersistance('tester')
        assert not op.get()
        offset=1337
        op.set(offset)
        ret=op.get()
        assert ret==offset
