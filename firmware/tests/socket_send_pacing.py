# The Clonker 10000 - Experiment 7: HTTP send pacing
# CircuitPython 10.3.1 / Pico 2 W
# exec(open('/tests/socket_send_pacing.py').read())
import os
import time
import errno
import wifi
import socketpool
import gc

PORT = 9091
PAGE = '''<!doctype html><meta name="viewport" content="width=device-width"><title>Clonker pacing lab</title>
<h2>HTTP send pacing lab</h2>
<p>GET only. No flash writes.</p>
<label>Body bytes <input id="size" type="number" value="8700" min="1" max="40000"></label><br>
<label>Chunk bytes <input id="chunk" type="number" value="128" min="64" max="1460"></label><br>
<label>Send delay ms <input id="pace" type="number" value="0" min="0" max="100"></label><br>
<label>Connection cooldown ms <input id="cool" type="number" value="0" min="0" max="1000"></label><br>
<label>Cycles <input id="cycles" type="number" value="20" min="1" max="100"></label><br>
<button id="go">Start</button><pre id="out">Ready.</pre>
<script>
const el=id=>document.getElementById(id);
el('go').onclick=async()=>{
 const ids=['size','chunk','pace','cool','cycles'];
 if(!ids.every(id=>el(id).checkValidity())) return;
 const [size,chunk,pace,cool,cycles]=ids.map(id=>Number(el(id).value));
 el('go').disabled=true; el('out').textContent='Running...';
 let passed=0;
 try {
 for(let i=1;i<=cycles;i++){
 const start=performance.now();
 const ctl=new AbortController();
 const timer=setTimeout(()=>ctl.abort(),25000);
 try {
 const r=await fetch(`/probe/${size}/${chunk}/${pace}/${cool}/${i}`,{cache:'no-store',signal:ctl.signal});
 if(!r.ok)throw Error('HTTP '+r.status);
 const b=await r.text();
 if(b.length!==size || b!== 'X'.repeat(size))throw Error('Body mismatch '+b.length);
 passed++; el('out').textContent+=`\\n${i}: PASS ${Math.round(performance.now()-start)} ms`;
 } finally {clearTimeout(timer);}
 }
 } catch(e){el('out').textContent+='\\nFAILED: '+e.message;}
 finally{el('out').textContent+=`\\n${passed}/${cycles} passed`;el('go').disabled=false;}
};
</script>'''

def response(body, kind='text/plain', status='200 OK'):
    if isinstance(body, str):
        body = body.encode('utf-8')
    return ('HTTP/1.1 {}\r\nContent-Type: {}\r\nContent-Length: {}\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n'.format(status,kind,len(body))).encode() + body

if not wifi.radio.connected:
    wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
pool = socketpool.SocketPool(wifi.radio)
listener = pool.socket(pool.AF_INET,pool.SOCK_STREAM)
client = None
cool_until = 0
sequence = 0
try:
    listener.bind(('0.0.0.0',PORT))
    listener.listen(2)
    listener.settimeout(0)
    print('Pacing lab: http://{}:{}'.format(wifi.radio.ipv4_address,PORT))
    while True:
        if time.monotonic_ns() < cool_until:
            time.sleep(0.001)
            continue
        try:
            client, addr = listener.accept()
        except OSError as e:
            if e.errno != errno.EAGAIN:
                raise
            time.sleep(0.001)
            continue
        sequence += 1
        cooldown = 0
        try:
            client.settimeout(0)
            req = bytearray()
            buf = bytearray(512)
            start = time.monotonic_ns()
            while b'\r\n\r\n' not in req:
                if time.monotonic_ns()-start > 2_000_000_000 or len(req)>4096:
                    raise ValueError('Request timeout/limit')
                try:
                    n = client.recv_into(buf)
                except OSError as e:
                    if e.errno != errno.EAGAIN: raise
                    time.sleep(0.001)
                    continue
                if not n: raise ValueError('Peer closed')
                req.extend(memoryview(buf)[:n])
            method, path, _ = bytes(req).split(b'\r\n',1)[0].decode().split(' ',2)
            chunk, pace = 512, 0
            if method == 'GET' and path == '/':
                data = response(PAGE,'text/html')
            elif method == 'GET' and path.startswith('/probe/'):
                size, chunk, pace, cooldown, cycle = map(int,path.split('/')[2:])
                if not (1<=size<=40000 and 64<=chunk<=1460 and 0<=pace<=100 and 0<=cooldown<=1000):
                    raise ValueError('Invalid probe settings')
                data = response(b'X'*size)
            else:
                data = response('Not found',status='404 Not Found')
            sent = calls = slow = again = 0
            maximum = 0
            started = last = time.monotonic_ns()
            view = memoryview(data)
            print('#{} {} bytes={} chunk={} pace={} cool={} free={}'.format(sequence,path,len(data),chunk,pace,cooldown,gc.mem_free()))
            while sent < len(data):
                if time.monotonic_ns()-last > 4_000_000_000:
                    break
                before = sent
                t = time.monotonic_ns()
                calls += 1
                n = 0
                try:
                    n = client.send(view[sent:sent+chunk]) or 0
                except OSError as e:
                    if e.errno != errno.EAGAIN: raise
                    again += 1
                finally:
                    duration = time.monotonic_ns()-t
                    maximum = max(maximum,duration)
                    if duration > 20_000_000:
                        slow += 1
                        print('SLOW offset={} after={} count={} ms={:.1f}'.format(before,before+n,n,duration/1e6))
                sent += n
                if duration > 4_000_000_000:
                    break
                if n: last = time.monotonic_ns()
                if sent < len(data):
                    time.sleep(max(pace/1000,0.001))
            print('RESULT {} sent={}/{} calls={} EAGAIN={} slow={} max={:.1f}ms total={:.1f}ms'.format('PASS' if sent==len(data) and maximum<=4_000_000_000 else 'FAIL',sent,len(data),calls,again,slow,maximum/1e6,(time.monotonic_ns()-started)/1e6))
        except (OSError,ValueError) as e:
            print('CLIENT ERROR:',repr(e))
        finally:
            try: client.close()
            except OSError: pass
            client = None
            cool_until = time.monotonic_ns()+cooldown*1_000_000
except KeyboardInterrupt:
    print('Stopped')
finally:
    if client is not None:
        client.close()
    listener.close()
