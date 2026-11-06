import hashlib
import http.server
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import urllib.request
import unittest

SPEC = importlib.util.spec_from_file_location('apartment_serve', Path(__file__).parents[1] / 'serve.py')
serve = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(serve)


class VersionTest(unittest.TestCase):
    def test_page_and_version_use_content_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            old_here = serve.HERE
            serve.HERE = temp
            page = Path(temp) / 'index.html'
            source = b'<meta content="__APARTMENT_REVISION__">first'
            page.write_bytes(source)
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), serve.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f'http://127.0.0.1:{server.server_port}'
            try:
                def get(path):
                    with urllib.request.urlopen(base + path) as response:
                        self.assertIn('no-store', response.headers['Cache-Control'])
                        return response.read()

                revision = hashlib.sha256(source).hexdigest()
                self.assertIn(revision.encode(), get('/'))
                self.assertEqual(json.loads(get('/version.json'))['version'], revision)
                os.utime(page, None)
                self.assertEqual(json.loads(get('/version.json'))['version'], revision)
                page.write_bytes(source + b' changed')
                self.assertNotEqual(json.loads(get('/version.json'))['version'], revision)
            finally:
                server.shutdown()
                server.server_close()
                serve.HERE = old_here
                thread.join()


if __name__ == '__main__':
    unittest.main()
