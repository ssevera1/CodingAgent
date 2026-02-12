"""Tests for the agent engine (integration tests)."""

import os
import sys
import json
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.core.config import Config
from agent.core.engine import AgentEngine
from agent.core.llm import LLMClient


class TestEngineSetup(unittest.TestCase):
    """Test engine initialization and configuration."""

    def test_engine_creates_with_default_config(self):
        config = Config()
        config.web.enabled = False  # Don't need web for tests
        engine = AgentEngine(config)

        self.assertIsNotNone(engine.tools)
        self.assertIsNotNone(engine.conversation)
        self.assertIsNotNone(engine.llm)

    def test_engine_registers_tools(self):
        config = Config()
        config.web.enabled = True
        engine = AgentEngine(config)

        # Should have all tools registered
        self.assertIsNotNone(engine.tools.get("read_file"))
        self.assertIsNotNone(engine.tools.get("write_file"))
        self.assertIsNotNone(engine.tools.get("edit_file"))
        self.assertIsNotNone(engine.tools.get("list_directory"))
        self.assertIsNotNone(engine.tools.get("grep"))
        self.assertIsNotNone(engine.tools.get("glob"))
        self.assertIsNotNone(engine.tools.get("bash"))
        self.assertIsNotNone(engine.tools.get("git"))
        self.assertIsNotNone(engine.tools.get("web_search"))
        self.assertIsNotNone(engine.tools.get("web_fetch"))
        self.assertIsNotNone(engine.tools.get("scan_agents"))

    def test_engine_no_web_tools_when_disabled(self):
        config = Config()
        config.web.enabled = False
        engine = AgentEngine(config)

        self.assertIsNone(engine.tools.get("web_search"))
        self.assertIsNone(engine.tools.get("web_fetch"))
        self.assertIsNone(engine.tools.get("scan_agents"))

    def test_engine_system_prompt_set(self):
        config = Config()
        engine = AgentEngine(config)

        messages = engine.conversation.get_messages()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("CodeAgent", messages[0]["content"])

    def test_engine_reset(self):
        config = Config()
        engine = AgentEngine(config)

        engine.conversation.add_user("test")
        engine.conversation.add_assistant("response")
        engine.reset()

        messages = engine.conversation.get_messages()
        self.assertEqual(len(messages), 1)  # Only system prompt
        self.assertEqual(messages[0]["role"], "system")

    def test_update_working_directory(self):
        config = Config()
        engine = AgentEngine(config)

        tmpdir = tempfile.mkdtemp()
        try:
            engine.update_working_directory(tmpdir)
            self.assertEqual(config.agent.working_directory, tmpdir)
        finally:
            shutil.rmtree(tmpdir)


class TestToolCallParsing(unittest.TestCase):
    """Test tool call extraction from LLM responses."""

    def setUp(self):
        self.config = Config()
        self.config.web.enabled = False
        self.engine = AgentEngine(self.config)

    def test_extract_tool_call(self):
        content = '''Let me read that file.

```tool
{"tool": "read_file", "args": {"file_path": "main.py"}}
```

I'll check it now.'''

        calls = self.engine._extract_tool_calls(content)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["tool"], "read_file")
        self.assertEqual(calls[0]["args"]["file_path"], "main.py")

    def test_extract_multiple_tool_calls(self):
        content = '''```tool
{"tool": "read_file", "args": {"file_path": "a.py"}}
```

```tool
{"tool": "grep", "args": {"pattern": "def "}}
```'''

        calls = self.engine._extract_tool_calls(content)
        self.assertEqual(len(calls), 2)

    def test_no_tool_calls(self):
        content = "Here is a regular response with no tool calls."
        calls = self.engine._extract_tool_calls(content)
        self.assertEqual(len(calls), 0)

    def test_clean_content(self):
        content = '''Some text.

```tool
{"tool": "read_file", "args": {}}
```

More text.'''

        cleaned = self.engine._clean_content(content)
        self.assertNotIn("```tool", cleaned)
        self.assertIn("Some text.", cleaned)
        self.assertIn("More text.", cleaned)


class TestAutoApproval(unittest.TestCase):
    """Test tool auto-approval logic."""

    def setUp(self):
        self.config = Config()
        self.config.web.enabled = True
        self.engine = AgentEngine(self.config)

    def test_reads_auto_approved(self):
        self.assertTrue(self.engine._should_auto_approve("read_file", {}))
        self.assertTrue(self.engine._should_auto_approve("list_directory", {}))

    def test_searches_auto_approved(self):
        self.assertTrue(self.engine._should_auto_approve("grep", {}))
        self.assertTrue(self.engine._should_auto_approve("glob", {}))

    def test_writes_not_auto_approved(self):
        self.assertFalse(self.engine._should_auto_approve("write_file", {}))
        self.assertFalse(self.engine._should_auto_approve("edit_file", {}))

    def test_bash_not_auto_approved(self):
        self.assertFalse(self.engine._should_auto_approve("bash", {}))

    def test_web_auto_approved(self):
        self.assertTrue(self.engine._should_auto_approve("web_search", {}))
        self.assertTrue(self.engine._should_auto_approve("web_fetch", {}))
        self.assertTrue(self.engine._should_auto_approve("scan_agents", {}))

    def test_git_read_auto_approved(self):
        self.assertTrue(self.engine._should_auto_approve("git", {"command": "status"}))
        self.assertTrue(self.engine._should_auto_approve("git", {"command": "diff --staged"}))
        self.assertTrue(self.engine._should_auto_approve("git", {"command": "log --oneline"}))

    def test_git_write_not_auto_approved(self):
        self.assertFalse(self.engine._should_auto_approve("git", {"command": "commit -m 'x'"}))
        self.assertFalse(self.engine._should_auto_approve("git", {"command": "push"}))


if __name__ == "__main__":
    unittest.main()
