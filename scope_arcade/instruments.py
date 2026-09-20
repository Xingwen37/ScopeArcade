"""Exact-model presets validated on DHO4404 + SDG1032X. No FPGA programming."""
import math
import re
import pyvisa

def resource_manager():
    try:return pyvisa.ResourceManager()
    except Exception as exc:raise RuntimeError('未找到 VISA 运行库。USB 仪器请先安装 NI-VISA 或厂商兼容 VISA；仅电脑预览不需要 VISA。') from exc

def identify(inst,model):
    text=inst.query('*IDN?').strip()
    fields=[part.strip().upper() for part in text.split(',')]
    if len(fields)<2 or fields[1]!=model:raise ValueError(f'设备不匹配：需要 {model}，实际 {text}')
    return text

def parse_values(text):
    parts=text.partition(' ')[2].strip().split(',')
    return dict(zip(parts[::2],parts[1::2]))

def number(value):
    match=re.match(r'^[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?',value)
    if not match:raise ValueError(f'无效仪器数值：{value}')
    return float(match.group())

def verify_generator(wave,burst):
    w=parse_values(wave);b=parse_values(burst)
    if w.get('WVTP')!='PULSE' or b.get('TRSR')!='EXT' or b.get('GATE_NCYC')!='NCYC' or b.get('STATE')!='ON' or b.get('EDGE')!='RISE':
        raise ValueError('发生器外触发脉冲模式回读不正确')
    for key,expected in [('PERI',.0001),('AMP',2),('OFST',0),('WIDTH',.000076),('DLY',.000012)]:
        if key not in w or not math.isclose(number(w[key]),expected,rel_tol=.001,abs_tol=1e-10):
            raise ValueError(f'发生器 {key} 回读不正确')
    if number(b.get('TIME','0'))!=1:raise ValueError('发生器不是单周期 Burst')

def scope_error(scope):
    error=scope.query(':SYST:ERR?').strip()
    if not error.startswith('0,'):raise RuntimeError('示波器报告：'+error)

def configure_sessions(scope,generator,cancel=None):
    # Both identities must match before any output/state write.
    identities={'scope':identify(scope,'DHO4404'),'generator':identify(generator,'SDG1032X')}
    before={'generator':{q:generator.query(q).strip() for q in ['C1:OUTP?','C1:BSWV?','C1:BTWV?']},
            'scope':{q:scope.query(q).strip() for q in [':TIM:SCAL?',':ACQ:MDEP?',':TIM:XY:Z?',':CHAN3:DISP?']}}
    before['scope_errors']=[]
    for _ in range(10):
        error=scope.query(':SYST:ERR?').strip()
        if error.startswith('0,'):break
        before['scope_errors'].append(error)
    else:raise RuntimeError('示波器错误队列未清空，请检查仪器状态')
    generator.write('C1:OUTP OFF')
    try:
        for command in ['C1:OUTP LOAD,HZ','C1:BTWV STATE,OFF',
            'C1:BSWV WVTP,PULSE,PERI,0.0001,AMP,2,OFST,0,WIDTH,0.000076,DLY,0.000012']:
            generator.write(command)
        generator.query('*OPC?')
        generator.write('C1:BTWV STATE,ON,TRSR,EXT,GATE_NCYC,NCYC,TIME,1,DLAY,0,EDGE,RISE');generator.query('*OPC?')
        verify_generator(generator.query('C1:BSWV?').strip(),generator.query('C1:BTWV?').strip())
        for channel in (1,2,3):
            scope.write(f':CHAN{channel}:DISP ON');scope.query('*OPC?')
            for command in [f':CHAN{channel}:IMP OMEG',f':CHAN{channel}:COUP DC',f':CHAN{channel}:PROB 1',f':CHAN{channel}:OFFS 0']:
                scope.write(command)
            if channel<3:scope.write(f':CHAN{channel}:VERN ON')
            scope.write(f':CHAN{channel}:SCAL '+('0.4' if channel<3 else '0.5'))
        for command in [':CHAN1:BWL 20M',':CHAN2:BWL 20M',':TIM:SCAL 0.001',':ACQ:MDEP 100k',
                        ':DISP:GRAD:TIME MIN',':DISP:WBR 85',':TRIG:SWE AUTO',':TIM:XY:ENAB ON']:
            scope.write(command)
        scope.query('*OPC?')
        # DHO re-enabling XY can reset Z; set sources only AFTER enabling it.
        for command in [':TIM:XY:X CHAN1',':TIM:XY:Y CHAN2',':TIM:XY:Z CHAN3',':RUN']:scope.write(command)
        scope.query('*OPC?')
        if scope.query(':TIM:XY:Z?').strip()!='CHAN3':raise RuntimeError('示波器 Z 输入未选中 CH3')
        for channel in (1,2,3):
            if scope.query(f':CHAN{channel}:IMP?').strip()!='OMEG':raise RuntimeError('示波器必须使用 1 MΩ 输入')
            if scope.query(f':CHAN{channel}:COUP?').strip()!='DC':raise RuntimeError('示波器必须使用 DC 耦合')
            if float(scope.query(f':CHAN{channel}:OFFS?'))!=0 or float(scope.query(f':CHAN{channel}:PROB?'))!=1:
                raise RuntimeError('通道偏置/探头倍率回读不正确')
            expected=.4 if channel<3 else .5
            if not math.isclose(float(scope.query(f':CHAN{channel}:SCAL?')),expected):raise RuntimeError('通道量程回读不正确')
        scope_error(scope)
        if cancel and cancel.is_set():raise RuntimeError('操作已取消')
        return {'identity':identities,'before':before,'generator_enabled':False}
    except BaseException:
        generator.write('C1:OUTP OFF');raise

class Instruments:
    def discover(self):
        rm=resource_manager();result=[]
        try:
            for address in rm.list_resources():
                if not address.startswith(('USB','TCPIP')):continue
                inst=None
                try:
                    inst=rm.open_resource(address);inst.timeout=1800
                    result.append({'resource':address,'identity':inst.query('*IDN?').strip()})
                except Exception as exc:result.append({'resource':address,'identity':str(exc)})
                finally:
                    if inst:inst.close()
        finally:rm.close()
        return result

    def configure(self,scope_resource,generator_resource,cancel=None):
        rm=resource_manager();scope=generator=None
        try:
            scope=rm.open_resource(scope_resource);generator=rm.open_resource(generator_resource)
            scope.timeout=generator.timeout=3000
            return configure_sessions(scope,generator,cancel)
        finally:
            if generator:generator.close()
            if scope:scope.close()
            rm.close()

    def enable(self,scope_resource,generator_resource,cancel=None):
        rm=resource_manager();scope=generator=None
        try:
            scope=rm.open_resource(scope_resource);generator=rm.open_resource(generator_resource)
            scope.timeout=generator.timeout=3000
            identify(scope,'DHO4404');identify(generator,'SDG1032X')
            verify_generator(generator.query('C1:BSWV?').strip(),generator.query('C1:BTWV?').strip())
            if scope.query(':TIM:XY:Z?').strip()!='CHAN3' or scope.query(':CHAN3:IMP?').strip()!='OMEG':
                raise RuntimeError('CH3 消隐/阻抗配置不正确')
            if scope.query(':CHAN3:COUP?').strip()!='DC' or float(scope.query(':CHAN3:OFFS?'))!=0:
                raise RuntimeError('CH3 必须为 DC 耦合、零偏置')
            if cancel and cancel.is_set():raise RuntimeError('操作已取消')
            generator.write('C1:OUTP ON')
            if 'ON,' not in generator.query('C1:OUTP?').strip():raise RuntimeError('发生器输出未开启')
        except BaseException:
            if generator:generator.write('C1:OUTP OFF')
            raise
        finally:
            if generator:generator.close()
            if scope:scope.close()
            rm.close()

    def off(self,generator_resource):
        rm=resource_manager();generator=None
        try:
            generator=rm.open_resource(generator_resource);generator.timeout=2000
            identify(generator,'SDG1032X');generator.write('C1:OUTP OFF')
        finally:
            if generator:generator.close()
            rm.close()
