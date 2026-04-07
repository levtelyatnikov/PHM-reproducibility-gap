from __future__ import annotations

import unittest

from engine.judges import OpenRouterClient, extract_response_text


class JudgeClientTests(unittest.TestCase):
    def test_transport_stub_receives_payload_and_headers(self) -> None:
        seen: dict[str, object] = {}

        def transport(url: str, payload: bytes, headers: dict[str, str]) -> tuple[int, str]:
            seen["url"] = url
            seen["payload"] = payload
            seen["headers"] = headers
            return 200, '{"choices":[{"message":{"content":"A1"}}]}'

        client = OpenRouterClient(api_key="test-key", transport=transport)
        response = client.chat("test-model", [{"role": "user", "content": "hello"}])
        self.assertEqual(extract_response_text(response), "A1")
        self.assertEqual(seen["url"], client.base_url)
        self.assertIn(b'"model": "test-model"', seen["payload"])
        self.assertEqual(seen["headers"]["Authorization"], "Bearer test-key")


if __name__ == "__main__":
    unittest.main()

