"""Wire-compatible with racer_xy.fs / UserCode C48F."""
import binascii

MAX_LINES=72
BAUD=1000000

def validate_lines(lines):
    if not isinstance(lines,(list,tuple)) or not 1<=len(lines)<=MAX_LINES:
        raise ValueError('画面必须包含 1～72 条线段')
    result=[]
    for line in lines:
        if not isinstance(line,(list,tuple)) or len(line)!=4:
            raise ValueError('线段格式应为 (x0, y0, x1, y1)')
        if any(type(value) is not int or not 0<=value<=255 for value in line):
            raise ValueError('坐标必须是 0～255 的整数')
        result.append(tuple(line))
    return tuple(result)

def packet(sequence,lines):
    lines=validate_lines(lines)
    body=bytes([sequence&255,len(lines)])+bytes(v for line in lines for v in line)
    return b'\xa5\x5a'+body+binascii.crc_hqx(body,0xffff).to_bytes(2,'big')
