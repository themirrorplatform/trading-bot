// Minimal NinjaTrader 8 Add-On skeleton for local bridge
// Purpose: Local-only HTTP endpoints to accept commands and emit events.
// Notes: This is a conceptual scaffold; complete in NinjaTrader's AddOn environment.

using System;
using System.Net;
using System.Text;
using System.Threading;
using System.Collections.Concurrent;

namespace BotBridge.NinjaTrader
{
    public class LocalBridgeServer : IDisposable
    {
        private readonly HttpListener _listener;
        private readonly Thread _thread;
        private readonly BlockingCollection<string> _eventQueue = new BlockingCollection<string>(new ConcurrentQueue<string>());
        private volatile bool _running;
        private readonly string _authToken;

        public LocalBridgeServer(string prefix = "http://127.0.0.1:8123/", string authToken = "changeme")
        {
            _authToken = authToken;
            _listener = new HttpListener();
            _listener.Prefixes.Add(prefix);
            _thread = new Thread(Loop) { IsBackground = true };
        }

        public void Start()
        {
            _running = true;
            _listener.Start();
            _thread.Start();
        }

        public void Stop()
        {
            _running = false;
            try { _listener.Stop(); } catch { }
        }

        public void Dispose()
        {
            Stop();
            _listener.Close();
        }

        private bool Authorized(HttpListenerRequest req)
        {
            var token = req.Headers["X-Auth-Token"] ?? string.Empty;
            return token == _authToken;
        }

        private void Loop()
        {
            while (_running)
            {
                HttpListenerContext? ctx = null;
                try { ctx = _listener.GetContext(); } catch { if (!_running) break; }
                if (ctx == null) continue;
                var req = ctx.Request;
                var res = ctx.Response;
                try
                {
                    if (!Authorized(req)) { res.StatusCode = 401; res.Close(); continue; }
                    if (req.HttpMethod == "POST" && req.Url.AbsolutePath == "/command")
                    {
                        using var reader = new System.IO.StreamReader(req.InputStream, req.ContentEncoding);
                        var body = reader.ReadToEnd();
                        // TODO: parse JSON, map to NT API calls (On UI thread)
                        EnqueueEvent("{\"type\":\"Ack\",\"ok\":true}");
                        WriteJson(res, "{\"ok\":true}");
                    }
                    else if (req.HttpMethod == "GET" && req.Url.AbsolutePath == "/events")
                    {
                        // simple long-poll: return one event if available
                        if (_eventQueue.TryTake(out var evt, TimeSpan.FromMilliseconds(250)))
                            WriteJson(res, evt);
                        else
                            WriteJson(res, "{\"events\":[]}");
                    }
                    else
                    {
                        res.StatusCode = 404; res.Close();
                    }
                }
                catch
                {
                    res.StatusCode = 500; res.Close();
                }
            }
        }

        private static void WriteJson(HttpListenerResponse res, string json)
        {
            var buf = Encoding.UTF8.GetBytes(json);
            res.ContentType = "application/json";
            res.ContentEncoding = Encoding.UTF8;
            res.ContentLength64 = buf.Length;
            using var s = res.OutputStream;
            s.Write(buf, 0, buf.Length);
        }

        // Call from NT lifecycle hooks to emit events
        public void EnqueueEvent(string json)
        {
            _eventQueue.Add(json);
        }
    }
}
