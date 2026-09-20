import binascii
import json
from pathlib import Path
import tempfile
import time
import unittest
from scope_arcade.api import GameContext
from scope_arcade.plugins import discover,instantiate,install,read_game
from scope_arcade.protocol import packet,validate_lines
from scope_arcade.instruments import configure_sessions,verify_generator
from scope_arcade.transport import SerialTransport

ROOT=Path(__file__).resolve().parents[1]
WAVE='C1:BSWV WVTP,PULSE,PERI,0.0001S,AMP,2V,OFST,0V,WIDTH,7.6e-05,DLY,1.2e-05'
BURST='C1:BTWV STATE,ON,TRSR,EXT,GATE_NCYC,NCYC,TIME,1,EDGE,RISE'

class FakeInstrument:
    def __init__(self,model):self.model=model;self.calls=[];self.z='NONE';self.enabled=False
    def write(self,c):
        self.calls.append(c)
        if c==':TIM:XY:ENAB ON':self.z='NONE'
        if c==':TIM:XY:Z CHAN3':self.z='CHAN3'
    def query(self,q):
        self.calls.append(q)
        if q=='*IDN?':return f'Vendor,{self.model},test,1'
        if q=='C1:BSWV?':return WAVE
        if q=='C1:BTWV?':return BURST
        if q=='C1:OUTP?':return 'C1:OUTP OFF,LOAD,HZ'
        if q==':TIM:XY:Z?':return self.z
        if q.endswith(':IMP?'):return 'OMEG'
        if q.endswith(':COUP?'):return 'DC'
        if q.endswith(':OFFS?'):return '0'
        if q.endswith(':SCAL?'):return '.5' if 'CHAN3' in q else '.4'
        if q==':SYST:ERR?':return '0,"No error"'
        return '1'

class CoreTests(unittest.TestCase):
    def test_packet_matches_independent_crc(self):
        lines=[(1,2,3,4),(250,240,8,9)];data=packet(257,lines)
        self.assertEqual(data[:4],b'\xa5\x5a\x01\x02')
        self.assertEqual(int.from_bytes(data[-2:],'big'),binascii.crc_hqx(data[2:-2],0xffff))

    def test_reject_invalid_game_frames(self):
        for lines in [[],[(0,0,1,256)],[(True,0,1,1)],[(0.,0,1,1)],[(0,0,1,1)]*73]:
            with self.assertRaises(ValueError):validate_lines(lines)

    def test_all_builtin_games_and_switching(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);games,errors=discover(ROOT/'games',root/'games');self.assertFalse(errors)
            self.assertEqual({g.id for g in games},{'racer','pong','dino','bad-apple'})
            for info in games:
                data=root/info.id;data.mkdir();g=instantiate(info,GameContext(data,'测试玩家',lambda _:None))
                for i in range(400):
                    g.update(1/120,{'right'}, {'space'} if i==0 else set())
                    if i%20==0:validate_lines(g.lines())
                self.assertIsInstance(g.status(),str)
            # Reimporting the first game must not reuse another game's model module.
            again=instantiate(games[0],GameContext(root/games[0].id,'测试',lambda _:None));validate_lines(again.lines())

    def test_import_template_duplicate_and_traversal(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);info=install(ROOT/'game-template',root,{'pong','dino','racer'})
            game=instantiate(info,GameContext(root/'state','测试',lambda _:None));validate_lines(game.lines())
            with self.assertRaises(ValueError):install(ROOT/'game-template',root,{info.id})
            unsafe=root/'unsafe';unsafe.mkdir();(root/'outside.py').write_text('raise AssertionError("must not execute")')
            (unsafe/'game.json').write_text(json.dumps({'api_version':1,'id':'unsafe','name':'Unsafe','entry':'../outside.py'}))
            with self.assertRaises(ValueError):read_game(unsafe)

    def test_instruments_output_off_and_xy_order(self):
        s=FakeInstrument('DHO4404');g=FakeInstrument('SDG1032X');report=configure_sessions(s,g)
        writes=[x for x in g.calls if not x.endswith('?')]
        self.assertEqual(writes[0],'C1:OUTP OFF');self.assertNotIn('C1:OUTP ON',writes)
        self.assertLess(s.calls.index(':TIM:XY:ENAB ON'),s.calls.index(':TIM:XY:Z CHAN3'))
        self.assertFalse(report['generator_enabled'])

    def test_wrong_model_has_no_writes(self):
        s=FakeInstrument('WRONG');g=FakeInstrument('SDG1032X')
        with self.assertRaises(ValueError):configure_sessions(s,g)
        self.assertFalse(any(not x.endswith('?') for x in s.calls+g.calls))

    def test_generator_readback_rejection(self):
        verify_generator(WAVE,BURST)
        for wave,burst in [(WAVE.replace('AMP,2V','AMP,20V'),BURST),(WAVE,BURST.replace('TRSR,EXT','TRSR,INT'))]:
            with self.assertRaises(ValueError):verify_generator(wave,burst)

    def test_resume_starts_new_ack_grace_window(self):
        link=type('Link',(),{'port':'fake'})();t=SerialTransport(link);t.last_ack=time.monotonic()-5
        t.frame([(0,0,1,1)]);self.assertLess(t.snapshot()['stream_age'],.1)
        t.frame(None);self.assertEqual(t.snapshot()['stream_age'],0)

if __name__=='__main__':unittest.main()
