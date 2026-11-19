"""CPU test: the connection is separate from the settings, parsed from what users paste, written atomically and re-read at every use."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
tmp = tempfile.mkdtemp()
os.environ["LAYERPROTO_CONNECTION_FILE"] = os.path.join(tmp, "sub", "connection.json")
for k in ("LAYERPROTO_URL", "LAYERPROTO_TOKEN"):
    os.environ.pop(k, None)
from layerproto import config, connection  # noqa: E402

# 1. parse every format a user might paste
U = "https://door-predict-loud.trycloudflare.com"
for text in (f"LAYERPROTO-CONNECT {U}|tok_123", f"{U}|tok_123", f"{U} tok_123", f"some log\nLAYERPROTO-CONNECT {U}|tok_123\nmore log",
             json.dumps({"remote_url": U + "/", "remote_token": "tok_123"}, indent=1), 'Put this:\n{\n "remote_url": "%s",\n "remote_token": "tok_123"\n}' % U):
    assert connection.parse(text) == (U, "tok_123"), (text, connection.parse(text))
assert connection.parse(U) == (U, "")
for bad in ("", "no url here", "tok_123"):
    try:
        connection.parse(bad)
        raise SystemExit(f"should have failed: {bad!r}")
    except ValueError:
        pass

# 2. nothing connected yet
assert not connection.load().configured
assert connection.check()["ok"] is False

# 3. save then load, in a folder that did not exist; a later save replaces the first (new Kaggle session)
connection.save(U, "tok_123", "qwen21")
c = connection.load()
assert (c.url, c.token, c.profile) == (U, "tok_123", "qwen21") and c.configured
connection.save("https://second.trycloudflare.com", "tok_456")
assert connection.load().url == "https://second.trycloudflare.com" and connection.load().token == "tok_456"
assert [f for f in os.listdir(os.path.dirname(connection.path())) if f.endswith(".tmp")] == [], "temp file left behind"

# 4. THE BUG: saving the settings must never touch the connection, and must not contain it
s = config.Settings()
assert not hasattr(s, "remote_url") and not hasattr(s, "remote_token")
cfg_dir = tempfile.mkdtemp()
config.CONFIG_PATH = os.path.join(cfg_dir, "config.json")
config.Settings().save()
saved = json.load(open(config.CONFIG_PATH))
assert "remote_url" not in saved and "remote_token" not in saved
assert connection.load().token == "tok_456", "saving settings changed the connection"

# 5. the file is read at every use: an edit made while the app runs is seen without a restart
json.dump({"url": "https://third.trycloudflare.com", "token": "tok_789"}, open(connection.path(), "w"))
assert connection.load().url == "https://third.trycloudflare.com"

# 6. environment override, and a legacy config.json is only a fallback
os.environ["LAYERPROTO_URL"], os.environ["LAYERPROTO_TOKEN"] = "https://env.example", "envtok"
assert connection.load().url == "https://env.example"
del os.environ["LAYERPROTO_URL"], os.environ["LAYERPROTO_TOKEN"]
connection.clear()
assert not connection.load().configured

# 7. two roles live side by side; clearing one keeps the other; an old flat file counts as "split"
connection.save("https://gen.trycloudflare.com", "g", "sdxl-turbo", role="generate")
connection.save("https://spl.trycloudflare.com", "s", "qwen21", role="split")
assert connection.load("generate").url.endswith("gen.trycloudflare.com") and connection.load("split").url.endswith("spl.trycloudflare.com")
connection.clear("generate")
assert not connection.load("generate").configured and connection.load("split").configured
json.dump({"url": "https://old.trycloudflare.com", "token": "o"}, open(connection.path(), "w"))
assert connection.load("split").url == "https://old.trycloudflare.com" and not connection.load("generate").configured
connection.clear()

# 8. no model or Ollama setting is left, and the LLM module is gone
assert not any(k in vars(s) for k in ("llm_model", "ollama_url", "captioner", "image_backend", "sdxl_model", "step_refine"))
try:
    import layerproto.llm  # noqa: F401
    raise AssertionError("layerproto.llm should be gone")
except ImportError:
    pass
print("connection test passed")
